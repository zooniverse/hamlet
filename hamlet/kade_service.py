import os
from urllib.parse import urlparse

class MissingKadeServiceUrl(Exception):
    pass


def env_string():
    # determine the kade environment based on the DJANGO environment
    return 'production' if os.environ.get('DJANGO_ENV') == 'production' else 'staging'

def env_string_upcase():
    return env_string().upper()

def public_url():
    if env_string() == 'production':
        return 'https://kade.zooniverse.org'
    else:
        return 'https://kade-staging.zooniverse.org'


def url():
    # allow service URL to be set by env vars
    kade_service_url = os.environ.get('KADE_SUBJECT_ASSISTANT_SERVICE_URL')
    if kade_service_url:
        return kade_service_url

    # construct the KaDE service host ENV name from K8s env vars
    # this will be an internal k8s cluster host DNS so avoids routing through the internet
    kade_service_host = os.environ.get(f'KADE_{env_string_upcase()}_APP_SERVICE_HOST')
    if not kade_service_host:
      raise MissingKadeServiceUrl('Please set the KaDE service URL in the KADE_SUBJECT_ASSISTANT_SERVICE_URL env var')

    return f'http://{kade_service_host}/prediction_jobs'

def http_url():
    return urlparse(url()).scheme == 'http'

def headers():
    headers = {'Content-Type': 'application/json'}
    if http_url():
        # simulate ingress TLS terminated traffic for internal K8s traffic
        # as KaDE only allow secure protocol HTTP traffic
        headers.update({'X-Forwarded-Proto': 'https'})

    return headers

# configure the KaDE API basic auth credentials
def basic_auth_username():
    return os.environ.get('KADE_API_BASIC_AUTH_USERNAME')

def basic_auth_password():
    return os.environ.get('KADE_API_BASIC_AUTH_PASSWORD')
