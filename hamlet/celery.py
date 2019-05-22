from __future__ import absolute_import, unicode_literals

import os
from datetime import datetime, timedelta

import django
from celery import Celery

from panoptes_client import Panoptes, SubjectSet

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hamlet.settings')
django.setup()

from django.conf import settings

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
    subject_set_id,
    access_token,
    extra_data,
):
    with Panoptes() as p:
        p.bearer_token = access_token
        p.logged_in = True
        p.refresh_token = extra_data['refresh_token']
        p.bearer_expires = (
                datetime.fromtimestamp(extra_data['auth_time'])
                + timedelta(extra_data['expires_in'])
            )

        subject_set = SubjectSet.find(subject_set_id)
        print('Subject set: {}'.format(subject_set.display_name))
