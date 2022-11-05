from datetime import datetime, timedelta

from django.conf import settings

from social_core.backends.oauth import BaseOAuth2
from panoptes_client import Panoptes, ProjectRole

import os

class ZooniverseOAuth2(BaseOAuth2):
    name = 'zooniverse'
    AUTHORIZATION_URL = os.getenv('OAUTH_AUTHORIZATION_URL', 'https://www.zooniverse.org/oauth/authorize')
    ACCESS_TOKEN_URL = os.getenv('OAUTH_ACCESS_TOKEN_URL', 'https://www.zooniverse.org/oauth/token')
    ACCESS_TOKEN_METHOD = 'POST'
    REVOKE_TOKEN_URL = os.getenv('OAUTH_REVOKE_TOKEN_URL', 'https://www.zooniverse.org/oauth/revoke')
    REVOKE_TOKEN_METHOD = 'GET'
    # ensure we store the expires_in time of the token
    # this is used to set the default django session length
    # and ensure the user has to log in again to gain access
    # and avoids having expired tokens / 403 access errors to restricted API resources
    EXTRA_DATA = [
        ('expires_in', 'expires')
    ]

    def get_user_details(self, response):
        with SocialPanoptes(bearer_token=response['access_token']) as sp:
            return {
                'username': sp.me['login'],
                'email': sp.me['email'],
            }

    def get_user_id(self, details, response):
        return details['username']


class SocialPanoptes(Panoptes):
    def __init__(
        self,
        endpoint=settings.ZOONIVERSE_API_ENDPOINT,
        client_id=settings.SOCIAL_AUTH_ZOONIVERSE_KEY,
        client_secret=None,
        redirect_url=None,
        username=None,
        password=None,
        login=None,
        admin=False,
        bearer_token=None,
    ):
        super().__init__(
            endpoint=endpoint,
            client_id=client_id,
            client_secret=client_secret,
            redirect_url=redirect_url,
            username=username,
            password=password,
            login=login,
            admin=admin,
        )
        self.bearer_token = bearer_token
        self.logged_in = True
        self._me = None

    def collab_for_project(self, project_id):
        if not self.me:
            return False

        for role in ProjectRole.where(
            project_id=project_id,
            user_id=self.me['id'],
        ):
            if (
                'owner' in role.roles or
                'collaborator' in role.roles
            ):
                return True
        return False


    def get_bearer_token(self):
        # Don't attempt to check if the token is valid or to refresh it
        # social_core should handle this
        return self.bearer_token

    @property
    def me(self):
        if not self._me:
            try:
                self._me = self.get('/me')[0]['users'][0]
            except TypeError:
                pass
        return self._me
