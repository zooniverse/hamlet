import os

def env_string():
    # determine the kade environment based on the DJANGO environment
    return 'production' if os.environ.get('DJANGO_ENV') == 'production' else 'staging'

def env_string_upcase():
    return env_string().upper()

def url():
    # allow service URL to be set by env vars
    kade_service_url = os.environ.get('KADE_SUBJECT_ASSISTANT_SERVICE_URL')
    if kade_service_url:
        return kade_service_url

    # construct the KaDE service host ENV name from K8s env vars
    # this will be an internal k8s cluster host DNS so avoids routing through the internet
    kade_service_host = os.environ.get(
      f'KADE_{env_string_upcase()}_APP_SERVICE_HOST', 'kade-staging.zooniverse.org')
    return f'http://{kade_service_host}/prediction_jobs'


# configure the KaDE API basic auth credentials
def basic_auth_username():
    return os.environ.get('KADE_API_BASIC_AUTH_USERNAME')

def basic_auth_password():
    return os.environ.get('KADE_API_BASIC_AUTH_PASSWORD')
