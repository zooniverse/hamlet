from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from panoptes_client import Panoptes, Project, SubjectSet, Workflow

from exports.forms import WorkflowExportForm
from exports.models import SubjectSetExport, WorkflowExport, MLSubjectAssistantExport
from .celery import subject_set_export, workflow_export, ml_subject_assistant_export_to_microsoft
from .zooniverse_auth import SocialPanoptes


@login_required
def index(request):
    social = request.user.social_auth.get(provider='zooniverse')
    with SocialPanoptes(bearer_token=social.access_token) as p:
        context = {
            'projects': Project.where(owner=request.user.username),
        }

        return render(request, 'index.html', context)


@login_required
def project(request, project_id):
    social = request.user.social_auth.get(provider='zooniverse')
    with SocialPanoptes(bearer_token=social.access_token) as p:
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
    social = request.user.social_auth.get(provider='zooniverse')
    with SocialPanoptes(bearer_token=social.access_token) as p:
        if not p.collab_for_project(project_id):
            raise PermissionDenied
    export = SubjectSetExport.objects.create(subject_set_id=subject_set_id)
    task_result = subject_set_export.delay(
        export.id,
        social.access_token,
    )
    export.celery_task = task_result.id
    export.save()
    return redirect('project', project_id=project_id)


@login_required
@require_POST
def workflow(request, workflow_id, project_id):
    form = WorkflowExportForm(request.POST)
    if form.is_valid():
        social = request.user.social_auth.get(provider='zooniverse')
        with SocialPanoptes(bearer_token=social.access_token) as p:
            if not p.collab_for_project(project_id):
                raise PermissionDenied
        export = WorkflowExport.objects.create(workflow_id=workflow_id)
        task_result = workflow_export.delay(
            export.id,
            social.access_token,
            form.cleaned_data['storage_prefix'],
        )
        export.celery_task = task_result.id
        export.save()
    return redirect('project', project_id=project_id)


@login_required
def ml_subject_assistant_list(request, project_id):
    social = request.user.social_auth.get(provider='zooniverse')
    with SocialPanoptes(bearer_token=social.access_token) as p:

        if not p.collab_for_project(project_id):
            raise PermissionDenied

        ml_subject_assistant_exports = []

        for subject_set in SubjectSet.where(project_id=project_id):
            ml_subject_assistant_exports.append((
                subject_set,
                MLSubjectAssistantExport.objects.filter(
                    subject_set_id=subject_set.id
                ).order_by('-created'),
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
    # Check permissions
    social = request.user.social_auth.get(provider='zooniverse')
    with SocialPanoptes(bearer_token=social.access_token) as p:
        if not p.collab_for_project(project_id):
            raise PermissionDenied
    
    # Create data export
    export = MLSubjectAssistantExport.objects.create(subject_set_id=subject_set_id)
    task_result = ml_subject_assistant_export_to_microsoft.delay(
        export.id,
        social.access_token,
    )
    export.celery_task = task_result.id
    export.save()
    return redirect('ml_subject_assistant_list', project_id=project_id)
