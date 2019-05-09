from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from panoptes_client import Panoptes, Project


@login_required
def index(request):
    social = request.user.social_auth.get(provider='zooniverse')
    with Panoptes() as p:
        p.bearer_token = social.access_token
        p.logged_in = True
        p.refresh_token = social.refresh_token
        p.bearer_expires = (
                datetime.fromtimestamp(social.extra_data['auth_time'])
                + timedelta(social.extra_data['expires_in'])
            )

        context = {
            'projects': Project.where(owner=request.user.username),
        }

        return render(request, 'index.html', context)
