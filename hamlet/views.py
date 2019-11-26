from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from panoptes_client import Panoptes, Project, SubjectSet, Workflow

from social_django.utils import load_strategy

from exports.forms import WorkflowExportForm
from exports.models import SubjectSetExport, WorkflowExport, MLSubjectAssistantExport
from .celery import subject_set_export, workflow_export, ml_subject_assistant_export_to_microsoft
from .zooniverse_auth import SocialPanoptes


def social_context(request):
    social = request.user.social_auth.get(provider='zooniverse')
    return SocialPanoptes(bearer_token=social.get_access_token(load_strategy()))


@login_required
def index(request):
    with social_context(request) as p:
        context = {
            'projects': Project.where(owner=request.user.username),
        }

        return render(request, 'index.html', context)


@login_required
def project(request, project_id):
    with social_context(request) as p:
        if not p.collab_for_project(project_id):
            raise PermissionDenied

        subject_set_exports = []

        for subject_set in SubjectSet.where(project_id=project_id):
            subject_set_exports.append((
                subject_set,
                SubjectSetExport.objects.filter(
                    subject_set_id=subject_set.id
                ).order_by('-created'),
            ))

        workflow_exports = []

        for workflow in Workflow.where(project_id=project_id):
            workflow_exports.append((
                workflow,
                WorkflowExport.objects.filter(
                    workflow_id=workflow.id,
                ).order_by('-created'),
            ))

        context = {
            'project': Project.find(
                id=project_id,
            ),
            'subject_set_exports': subject_set_exports,
            'workflow_exports': workflow_exports,
            'workflow_export_form': WorkflowExportForm(),
        }

        return render(request, 'project.html', context)


@login_required
@require_POST
def subject_set(request, subject_set_id, project_id):
    with social_context(request) as p:
        if not p.collab_for_project(project_id):
            raise PermissionDenied
        export = SubjectSetExport.objects.create(subject_set_id=subject_set_id)
        task_result = subject_set_export.delay(
            export.id,
            p.bearer_token,
        )
        export.celery_task = task_result.id
        export.save()
    return redirect('project', project_id=project_id)


@login_required
@require_POST
def workflow(request, workflow_id, project_id):
    form = WorkflowExportForm(request.POST)
    if form.is_valid():
        with social_context(request) as p:
            if not p.collab_for_project(project_id):
                raise PermissionDenied
            access_token = p.bearer_token
            export = WorkflowExport.objects.create(workflow_id=workflow_id)
            task_result = workflow_export.delay(
                export.id,
                p.bearer_token,
                form.cleaned_data['storage_prefix'],
            )
            export.celery_task = task_result.id
            export.save()
    return redirect('project', project_id=project_id)


@login_required
def ml_subject_assistant_list(request, project_id):
    """List Page: shows all Subject Sets for a specific Project."""
  
    with social_context(request) as p:
        if not p.collab_for_project(project_id):
            raise PermissionDenied

        ml_subject_assistant_exports = []

        for subject_set in SubjectSet.where(project_id=project_id):
            data_export = MLSubjectAssistantExport.objects.filter(
                subject_set_id=subject_set.id
            ).order_by('-created')
            
            external_web_app_url = 'https://subject-assistant.zooniverse.org/#/tasks/'
            if list(data_export)[0].ml_task_id:
                external_web_app_url = external_web_app_url + str(list(data_export)[0].ml_task_id)
          
            ml_subject_assistant_exports.append((
                subject_set,
                data_export,
                external_web_app_url
            ))

        context = {
            'project': Project.find(
                id=project_id,
            ),
            'ml_subject_assistant_exports': ml_subject_assistant_exports
        }

        return render(request, 'ml-subject-assistant.html', context)


@login_required
@require_POST
def ml_subject_assistant_export(request, subject_set_id, project_id):
    """Export Action: sets up a Subject Set to be exported to a machine learning server."""
  
    # Check permissions
    with social_context(request) as p:
        if not p.collab_for_project(project_id):
            raise PermissionDenied
    
        # Create data export
        export = MLSubjectAssistantExport.objects.create(
            subject_set_id=subject_set_id,
        )
        task_result = ml_subject_assistant_export_to_microsoft.delay(
            export.id,
            p.bearer_token,
        )
        export.celery_task = task_result.id
        export.save()
    return redirect('ml_subject_assistant_list', project_id=project_id)
