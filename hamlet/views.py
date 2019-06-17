from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from panoptes_client import Panoptes, Project, SubjectSet, Workflow

from exports.forms import WorkflowExportForm
from exports.models import SubjectSetExport, WorkflowExport
from .celery import subject_set_export, workflow_export


@login_required
def index(request):
    social = request.user.social_auth.get(provider='zooniverse')
    with Panoptes() as p:
        p.bearer_token = social.access_token
        p.logged_in = True
        p.refresh_token = social.extra_data['refresh_token']
        p.bearer_expires = (
                datetime.fromtimestamp(social.extra_data['auth_time'])
                + timedelta(social.extra_data['expires_in'])
            )

        context = {
            'projects': Project.where(owner=request.user.username),
        }

        return render(request, 'index.html', context)


@login_required
def project(request, project_id):
    social = request.user.social_auth.get(provider='zooniverse')
    with Panoptes() as p:
        p.bearer_token = social.access_token
        p.logged_in = True
        p.refresh_token = social.extra_data['refresh_token']
        p.bearer_expires = (
                datetime.fromtimestamp(social.extra_data['auth_time'])
                + timedelta(social.extra_data['expires_in'])
            )

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
def subject_set(request, subject_set_id, project_id):
    social = request.user.social_auth.get(provider='zooniverse')
    export = SubjectSetExport.objects.create(subject_set_id=subject_set_id)
    subject_set_export.delay(
        export.id,
        social.access_token,
        social.extra_data,
    )
    return redirect('project', project_id=project_id)


@login_required
def workflow(request, workflow_id, project_id):
    if request.method == 'POST':
        form = WorkflowExportForm(request.POST)
        if form.is_valid():
            social = request.user.social_auth.get(provider='zooniverse')
            with Panoptes() as p:
                p.bearer_token = social.access_token
                p.logged_in = True
                p.refresh_token = social.extra_data['refresh_token']
                p.bearer_expires = (
                        datetime.fromtimestamp(social.extra_data['auth_time'])
                        + timedelta(social.extra_data['expires_in'])
                    )

            export = WorkflowExport.objects.create(workflow_id=workflow_id)
            workflow_export.delay(
                export.id,
                social.access_token,
                social.extra_data,
                form.cleaned_data['storage_prefix'],
            )
    return redirect('project', project_id=project_id)
