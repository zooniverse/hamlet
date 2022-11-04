from __future__ import absolute_import, unicode_literals

import base64
import csv
import hashlib
import os
import re
import tempfile

import django
import requests

from celery import Celery
from celery.exceptions import MaxRetriesExceededError

from panoptes_client import Panoptes, SubjectSet, Workflow

from azure.storage.blob import BlockBlobService, BlobPermissions

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hamlet.settings')
django.setup()

from django.conf import settings
from django.core.files import File

from exports.models import SubjectSetExport, MediaMetadata, WorkflowExport, MLSubjectAssistantExport, KadeSubjectAssistantExport
from .zooniverse_auth import SocialPanoptes
from . import ms_ml_exports
from . import kade_ml_exports
from . import kade_service

app = Celery('hamlet', broker=settings.REDIS_URI, backend=settings.REDIS_URI)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means al§l celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def subject_set_export(
    self,
    export_id,
    access_token,
):
    export = SubjectSetExport.objects.get(pk=export_id)
    try:
        export.status = SubjectSetExport.RUNNING
        export.save()
        with SocialPanoptes(bearer_token=access_token) as p:
            subject_set = SubjectSet.find(export.subject_set_id)
            for subject in subject_set.subjects:
                for location in subject.locations:
                    media_metadata = MediaMetadata.objects.create(
                        export=export,
                        subject_id=subject.id,
                        url=list(location.values())[0],
                    )
                    task_result = fetch_media_metadata.delay(media_metadata.id)
                    media_metadata.celery_task = task_result.id
                    media_metadata.save()

            task_result = update_subject_set_export_status.delay(export_id)
            export.celery_task = task_result.id
            export.save()
    except:
        export.status = SubjectSetExport.FAILED
        export.save()
        raise


@app.task(bind=True)
def update_subject_set_export_status(
    self,
    export_id,
):
    export = SubjectSetExport.objects.get(pk=export_id)
    try:
        pending_metadata = export.mediametadata_set.filter(
            status=MediaMetadata.PENDING,
        )
        if pending_metadata.count() > 0:
            for mediametadata in pending_metadata:
                mediametadata.check_status()
            task_result = update_subject_set_export_status.apply_async(
                args=(export_id,),
                countdown=10,
            )
            export.celery_task = task_result.id
            export.save()
            return

        if export.mediametadata_set.filter(
            status=SubjectSetExport.FAILED
        ).count() > 0:
            export.status = SubjectSetExport.FAILED
            export.save()
        else:
            task_result = write_subject_set_export.delay(export_id)
            export.celery_task = task_result.id
            export.save()
    except:
        export.status = SubjectSetExport.FAILED
        export.save()
        raise


@app.task(bind=True)
def fetch_media_metadata(self, media_metadata_id):
    media_metadata = MediaMetadata.objects.get(pk=media_metadata_id)
    try:
        media_metadata.status = MediaMetadata.RUNNING
        media_metadata.save()

        r = requests.get(media_metadata.url)
        r.raise_for_status()

        media_metadata.filesize = len(r.content)
        media_metadata.hash = base64.b64encode(
            hashlib.md5(r.content).digest()
        ).decode()

        media_metadata.status = MediaMetadata.COMPLETE
        media_metadata.save()
    except Exception as e:
        try:
            self.retry(countdown=60)
        except MaxRetriesExceededError:
            media_metadata.status = MediaMetadata.FAILED
            media_metadata.save()
            raise e


@app.task(bind=True)
def write_subject_set_export(self, export_id):
    export = SubjectSetExport.objects.get(pk=export_id)
    try:
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
        export.status = SubjectSetExport.COMPLETE
        export.save()
    except Exception as e:
        try:
            self.retry(countdown=60)
        except MaxRetriesExceededError:
            export.status = SubjectSetExport.FAILED
            export.save()
            raise e
    finally:
        os.unlink(out_f_name)


class ExportFailure(Exception):
    pass


@app.task(bind=True)
def workflow_export(
    self,
    export_id,
    access_token,
    storage_prefix,
):
    export = WorkflowExport.objects.get(pk=export_id)
    export.status = WorkflowExport.RUNNING
    export.save()

    try:
        with SocialPanoptes(bearer_token=access_token) as p:
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

            export.status = WorkflowExport.COMPLETE
            export.save()
    except Exception as e:
        try:
            self.retry(countdown=60)
        except MaxRetriesExceededError:
            export.status = WorkflowExport.FAILED
            export.save()
            raise e
    finally:
        os.unlink(out_f_name)


@app.task(bind=True)
def ml_subject_assistant_export_to_microsoft(
    self,
    export_id,
    access_token,
):
    r"""Export a 'subject manifest' for the Microsoft ML server.

    Creates a JSON file which details all the image URLs in a Subject Set, along
    with that image's associated Subject information. JSON will be formatted so:

    [ [ "http://image.url/example.png",
       "{ \"subject_info\": \"is a stringified JSON object\" }" ],
      ... ]

    To be used with the Zooniverse ML Subject Assistant web app (https://github.com/zooniverse/zoo-ml-subject-assistant),
    and the associated (and currently unnamed) Microsoft machine learning
    service.
    """

    print('[Subject Assistant] Exporting to Microsoft')

    try:
        export = MLSubjectAssistantExport.objects.get(pk=export_id)
        target_filename = 'ml-subject-assistant-{}-export{}.json'.format(
            export.subject_set_id,
            export.id,
        )
        source_filepath = ''

        export.status = MLSubjectAssistantExport.RUNNING
        export.save()

        # Get the Subjects data
        data = ms_ml_exports.ml_subject_assistant_export_to_microsoft_pt1_get_subjects_data(export_id, access_token)

        # Create the file to be exported
        source_filepath = ms_ml_exports.ml_subject_assistant_export_to_microsoft_pt2_create_file(export_id, data, target_filename)

        # Upload the file to Azure, and get a shareable URL to the file
        shareable_file_url = ms_ml_exports.ml_subject_assistant_export_to_microsoft_pt3_create_shareable_azure_blob(source_filepath, target_filename)

        # Save the created file to the database
        # NOTE: this is technically optional, and only used as a backup
        with open(source_filepath, 'rb') as out_f:
            export.json.save(
                target_filename,
                File(out_f),
            )

        # Save a refrence to the shareable URL.
        # NOTE: these shareable URLs have a shelf life.
        export.azure_url = shareable_file_url

        # Submit the ML task request to the ML service
        export.ml_task_uuid = ms_ml_exports.ml_subject_assistant_export_to_microsoft_pt4_make_ml_request(shareable_file_url)

        # SUCCESS
        export.status = MLSubjectAssistantExport.COMPLETE
        export.save()

    except Exception as err:
        try:
            self.retry(countdown=60)
        except MaxRetriesExceededError:
            export.status = MLSubjectAssistantExport.FAILED
            export.save()
            raise err

    finally:
        # Clean up the temporary file, if it exists.
        try:
            if len(source_filepath) > 0:
                os.unlink(source_filepath)
        except OSError:
            pass


@app.task(bind=True)
def zoobot_subject_assistant_export_to_kade(
    self,
    export_id,
    access_token,
):
    r"""Export a 'subject manifest' for the KaDE ML prediction API service.

    Creates a JSON file which details all the image URLs in a Subject Set, along
    with that image's associated Subject information. JSON will be formatted so:

    [ [ "http://image.url/example.png",
       "{ \"subject_info\": \"is a stringified JSON object\" }" ],
      ... ]

    To be used with the Zooniverse ML Subject Assistant web app (https://github.com/zooniverse/zoo-ml-subject-assistant),
    and the associated KaDE's Zoobot Prediction ML service.
    """

    print('[Subject Assistant] Exporting to KaDE Zoobot Prediction Service')

    try:
        export = KadeSubjectAssistantExport.objects.get(pk=export_id)
        target_filename = 'zoobot-subject-assistant-{}-export{}.json'.format(
            export.subject_set_id,
            export.id,
        )
        source_filepath = ''

        export.status = KadeSubjectAssistantExport.RUNNING
        export.save()

        # Get the Subjects data
        data = kade_ml_exports.subject_assistant_export_get_subjects_data(export, access_token)

        # Create the file to be exported
        source_filepath = kade_ml_exports.subject_assistant_export_to_create_export_file(data)

        # Upload the file to Azure, and get a shareable URL to the file
        shareable_file_url = kade_ml_exports.subject_assistant_export_to_shareable_blob_storage_location(source_filepath, target_filename)

        # Save a refrence to the shareable URL.
        # NOTE: these shareable URLs have a shelf life.
        export.azure_url = shareable_file_url

        # Submit the ML task request to the ML service
        kade_service_job_id = kade_ml_exports.subject_assistant_export_to_kade(shareable_file_url)
        export.service_job_url = f'{kade_service.url()}/{kade_service_job_id}'

        # SUCCESS
        export.status = KadeSubjectAssistantExport.COMPLETE
        export.save()

    except Exception as err:
        try:
            self.retry(countdown=60)
        except MaxRetriesExceededError:
            export.status = KadeSubjectAssistantExport.FAILED
            export.save()
            raise err

    finally:
        # Clean up the temporary file, if it exists.
        try:
            if len(source_filepath) > 0:
                os.unlink(source_filepath)
        except OSError:
            pass
