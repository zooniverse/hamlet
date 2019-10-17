from celery.result import AsyncResult
from django.db import models


class StatusModel(models.Model):
    PENDING = 'p'
    RUNNING = 'r'
    COMPLETE = 'c'
    FAILED = 'f'

    TASK_STATUSES = {
        PENDING: 'Pending',
        RUNNING: 'Running',
        COMPLETE: 'Complete',
        FAILED: 'Failed',
    }

    TASK_CHOICES = list(TASK_STATUSES.items())

    status = models.CharField(
        max_length=1,
        choices=TASK_CHOICES,
        default=PENDING,
    )
    celery_task = models.UUIDField(null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def check_status(self):
        if self.status == self.PENDING and self.celery_task:
            if AsyncResult(self.celery_task).failed():
                self.status = self.FAILED
                self.save()

    def get_status_display(self):
        self.check_status()
        return StatusModel.TASK_STATUSES.get(self.status)


class SubjectSetExport(StatusModel):
    subject_set_id = models.IntegerField()
    csv = models.FileField(upload_to='subject_sets/', null=True)


class MediaMetadata(StatusModel):
    export = models.ForeignKey(SubjectSetExport, on_delete=models.CASCADE)
    subject_id = models.IntegerField()
    hash = models.CharField(max_length=32, null=True)
    filesize = models.IntegerField(null=True)
    url = models.URLField()


class WorkflowExport(StatusModel):
    workflow_id = models.IntegerField()
    csv = models.FileField(upload_to='workflows/', null=True)

class MLSubjectAssistantExport(StatusModel):
    subject_set_id = models.IntegerField()
    json = models.FileField(upload_to='ml_subject_assistant/', null=True)
