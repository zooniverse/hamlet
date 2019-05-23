from __future__ import absolute_import, unicode_literals

import hashlib
import os
from datetime import datetime, timedelta

import django
import requests

from celery import Celery

from panoptes_client import Panoptes, SubjectSet
from panoptes_client.panoptes import PanoptesAPIException

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hamlet.settings')
django.setup()

from django.conf import settings

from exports.models import SubjectSetExport, MediaMetadata

app = Celery('hamlet', broker=settings.REDIS_URI, backend=settings.REDIS_URI)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


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
        update_subject_set_export_status.delay(export_id)
        return

    if export.mediametadata_set.filter(status='f').count() > 0:
        export.status = 'f'
    else:
        export.status = 'c'

    export.save()


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
    media_metadata.hash = hashlib.md5(r.content).hexdigest()

    media_metadata.status = 'c'
    media_metadata.save()
