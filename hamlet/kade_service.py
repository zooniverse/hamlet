import os

def url():
    # construct the KaDE service host ENV name from K8s env vars
    # this will be an internal k8s cluster host DNS so avoids routing through the internet
    service_env = 'PRODUCTION' if os.environ.get('DJANGO_ENV') == 'production' else 'STAGING'
    # default to the externally hosted camera traps API service
    kade_service_host = os.environ.get(f'KADE_{service_env}_APP_SERVICE_HOST', 'kade-staging.zooniverse.org')
    return f'https://{kade_service_host}/prediction_jobs'


# configure the KaDE API basic auth credentials
def basic_auth_username():
    return os.environ.get('KADE_API_BASIC_AUTH_USERNAME')

def basic_auth_password():
    return os.environ.get('KADE_API_BASIC_AUTH_PASSWORD')