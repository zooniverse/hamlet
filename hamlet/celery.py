from __future__ import absolute_import, unicode_literals

import base64
import csv
import hashlib
import os
import re
import tempfile

from datetime import datetime, timedelta

import django
import requests

from celery import Celery

from panoptes_client import Panoptes, SubjectSet, Workflow
from panoptes_client.panoptes import PanoptesAPIException

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hamlet.settings')
django.setup()

from django.conf import settings
from django.core.files import File

from exports.models import SubjectSetExport, MediaMetadata, WorkflowExport

app = Celery('hamlet', broker=settings.REDIS_URI, backend=settings.REDIS_URI)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def subject_set_export(
    self,
    export_id,
    access_token,
    extra_data,
):
    export = SubjectSetExport.objects.get(pk=export_id)
    export.status = 'r'
    export.save()

    try:
        with Panoptes() as p:
            p.bearer_token = access_token
            p.logged_in = True
            p.refresh_token = extra_data['refresh_token']
            p.bearer_expires = (
                    datetime.fromtimestamp(extra_data['auth_time'])
                    + timedelta(extra_data['expires_in'])
                )

            subject_set = SubjectSet.find(export.subject_set_id)
            for subject in subject_set.subjects:
                for location in subject.locations:
                    media_metadata = MediaMetadata.objects.create(
                        export=export,
                        subject_id=subject.id,
                        url=list(location.values())[0],
                    )
                    fetch_media_metadata.delay(media_metadata.id)

            update_subject_set_export_status.delay(export_id)
    except PanoptesAPIException:
        export.status = 'f'
        export.save()


@app.task(bind=True)
def update_subject_set_export_status(
    self,
    export_id,
):
    export = SubjectSetExport.objects.get(pk=export_id)
    if export.mediametadata_set.filter(status='p').count() > 0:
        update_subject_set_export_status.apply_async(
            args=(export_id,),
            countdown=10,
        )
        return

    if export.mediametadata_set.filter(status='f').count() > 0:
        export.status = 'f'
        export.save()
    else:
        write_subject_set_export.delay(export_id)


@app.task(bind=True)
def fetch_media_metadata(self, media_metadata_id):
    media_metadata = MediaMetadata.objects.get(pk=media_metadata_id)

    r = requests.get(media_metadata.url)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        media_metadata.status = 'f'
        media_metadata.save()
        return

    media_metadata.filesize = len(r.content)
    media_metadata.hash = base64.b64encode(
        hashlib.md5(r.content).digest()
    ).decode()

    media_metadata.status = 'c'
    media_metadata.save()


@app.task(bind=True)
def write_subject_set_export(self, export_id):
    export = SubjectSetExport.objects.get(pk=export_id)
    with tempfile.NamedTemporaryFile(
        'w+',
        encoding='utf-8',
        dir=settings.TMP_STORAGE_PATH,
        delete=False,
    ) as out_f:
        csv_writer = csv.writer(out_f, dialect='excel-tab')
        csv_writer.writerow(['TsvHttpData-1.0'])
        for media_metadata in export.mediametadata_set.all():
            csv_writer.writerow([
                media_metadata.url,
                media_metadata.filesize,
                media_metadata.hash,
            ])
        out_f.flush()
        out_f_name = out_f.name
    with open(out_f_name, 'rb') as out_f:
        export.csv.save(
            'subject-set-{}-export{}.tsv'.format(
                export.subject_set_id,
                export.id,
            ),
            File(out_f),
        )
    os.unlink(out_f_name)
    export.status = 'c'
    export.save()

class ExportFailure(Exception):
    pass

@app.task(bind=True)
def workflow_export(
    self,
    export_id,
    access_token,
    extra_data,
    storage_prefix,
):
    export = WorkflowExport.objects.get(pk=export_id)
    export.status = 'r'
    export.save()

    try:
        with Panoptes() as p:
            p.bearer_token = access_token
            p.logged_in = True
            p.refresh_token = extra_data['refresh_token']
            p.bearer_expires = (
                    datetime.fromtimestamp(extra_data['auth_time'])
                    + timedelta(extra_data['expires_in'])
                )

            caesar_data_requests = requests.get(
                "{}/workflows/{}/data_requests".format(
                    settings.CAESAR_URL,
                    export.workflow_id,
                ),
                headers = {
                    'Authorization': "Bearer {}".format(p.get_bearer_token()),
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
            )
            caesar_data_requests.raise_for_status()
            caesar_data_requests = caesar_data_requests.json()

            if not caesar_data_requests:
                raise ExportFailure

            latest_reductions = None

            for data_request in sorted(
                caesar_data_requests,
                key=lambda req: req['updated_at'],
                reverse=True,
            ):
                if data_request['requested_data'] == 'subject_reductions':
                    latest_reductions = data_request

            if not latest_reductions:
                raise ExportFailure

            if not latest_reductions.get('url'):
                raise ExportFailure

            export_data = requests.get(latest_reductions.get('url')).content
            export_data = export_data.decode('utf-8')
            r = csv.DictReader(export_data.splitlines())
            subject_consensus = {}
            for row in r:
                if "data.most_likely" in row:
                    subject_consensus.setdefault(
                        int(row['subject_id']),
                        row['data.most_likely'],
                    )

            with tempfile.NamedTemporaryFile(
                'w+',
                encoding='utf-8',
                dir=settings.TMP_STORAGE_PATH,
                delete=False,
            ) as out_f:
                csv_writer = csv.writer(out_f)
                for media_metadata in MediaMetadata.objects.filter(
                    subject_id__in=subject_consensus.keys(),
                ).values('subject_id', 'url').distinct():
                    csv_writer.writerow([
                        "gs://{}/{}".format(
                            storage_prefix,
                            re.sub(r'^https?://', '', media_metadata['url']),
                        ),
                        subject_consensus[media_metadata['subject_id']],
                    ])

                out_f.flush()
                out_f_name = out_f.name

            with open(out_f_name, 'rb') as out_f:
                export.csv.save(
                    'workflow-{}-export{}.csv'.format(
                        export.workflow_id,
                        export.id,
                    ),
                    File(out_f),
                )
            os.unlink(out_f_name)

            export.status = 'c'
            export.save()
    except (
        ExportFailure,
        requests.exceptions.RequestException,
        PanoptesAPIException
    ):
        export.status = 'f'
        export.save()
        raise

