from datetime import datetime, timedelta

from social_core.backends.oauth import BaseOAuth2
from panoptes_client import Panoptes


class ZooniverseOAuth2(BaseOAuth2):
    name = 'zooniverse'
    AUTHORIZATION_URL = 'https://panoptes.zooniverse.org/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://panoptes.zooniverse.org/oauth/token'
    ACCESS_TOKEN_METHOD = 'POST'
    REVOKE_TOKEN_URL = 'https://panoptes.zooniverse.org/oauth/revoke'
    REVOKE_TOKEN_METHOD = 'GET'
    EXTRA_DATA = [
        ('expires_in', 'expires_in'),
        ('refresh_token', 'refresh_token'),
    ]

    def get_user_details(self, response):
        with Panoptes() as p:
            p.bearer_token = response['access_token']
            p.logged_in = True
            p.refresh_token = response['refresh_token']
            p.bearer_expires = (
                    datetime.now()
                    + timedelta(seconds=response['expires_in'])
                )

            user = p.get('/me')[0]['users'][0]
            return {
                'username': user['login'],
                'email': user['email'],
            }

    def get_user_id(self, details, response):
        return details['username']
