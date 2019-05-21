from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from panoptes_client import Panoptes, Project

from .celery import subject_set_export


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

        context = {
            'project': Project.find(
                id=project_id,
            ),
        }

        return render(request, 'project.html', context)


@login_required
def subject_set(request, subject_set_id, project_id):
    social = request.user.social_auth.get(provider='zooniverse')
    subject_set_export.delay(
        subject_set_id,
        social.access_token,
        social.extra_data,
    )
    return redirect('project', project_id=project_id)
