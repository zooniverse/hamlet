"""hamlet URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include, re_path
from django.conf import settings

from django.views.decorators.http import require_POST

import social_django.views

from hamlet import views


# Copied from https://github.com/python-social-auth/social-app-django/issues/55
social_urls = [
     # authentication / association
     re_path(
         'login/(?P<backend>[^/]+)/$',
         require_POST(social_django.views.auth),
         name='begin'
     ),
     re_path(
         r'^complete/(?P<backend>[^/]+)/$',
         social_django.views.complete,
         name='complete'
     ),
     # disconnection
     re_path(
         r'^disconnect/(?P<backend>[^/]+)/$',
         social_django.views.disconnect,
         name='disconnect'
     ),
     re_path(
         r'^disconnect/(?P<backend>[^/]+)/(?P<association_id>\d+)/$',
         social_django.views.disconnect,
         name='disconnect_individual'
     ),
 ]


urlpatterns = [
    path('', views.index, name='index'),
    path('', include((social_urls, 'social'))),
    path('projects/<int:project_id>/', views.project, name='project'),
    path(
        'projects/<int:project_id>/subject-sets/<int:subject_set_id>/',
        views.subject_set,
        name='subject_set'
    ),
    path(
        'projects/<int:project_id>/workflows/<int:workflow_id>/',
        views.workflow,
        name='workflow'
    ),
    path(
        'subject-assistant/<int:project_id>/',
        views.subject_assistant,
        name='subject_assistant'
    ),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
]
