from django.db import models


TASK_STATUSES = {
    'p': 'Pending',
    'r': 'Running',
    'c': 'Complete',
    'f': 'Failed',
}

TASK_CHOICES = list(TASK_STATUSES.items())


class SubjectSetExport(models.Model):
    subject_set_id = models.IntegerField()
    status = models.CharField(
        max_length=1,
        choices=TASK_CHOICES,
        default='p',
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    csv = models.FileField(upload_to='subject_sets/', null=True)

    def get_status_display(self):
        return TASK_STATUSES.get(self.status)


class MediaMetadata(models.Model):
    export = models.ForeignKey(SubjectSetExport, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=1,
        choices=TASK_CHOICES,
        default='p'
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    subject_id = models.IntegerField()
    hash = models.CharField(max_length=32, null=True)
    filesize = models.IntegerField(null=True)
    url = models.URLField()

class WorkflowExport(models.Model):
    workflow_id = models.IntegerField()
    status = models.CharField(
        max_length=1,
        choices=TASK_CHOICES,
        default='p',
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    csv = models.FileField(upload_to='workflows/', null=True)

    def get_status_display(self):
        return TASK_STATUSES.get(self.status)
