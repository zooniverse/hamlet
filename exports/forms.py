from django import forms

class WorkflowExportForm(forms.Form):
    storage_prefix = forms.CharField(
        label='Google Cloud Storage prefix',
        max_length=256,
    )
