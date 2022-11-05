"""
Django settings for hamlet project.

Generated by 'django-admin startproject' using Django 2.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    '%^y#%%ru2__e34ce7x8$wh4=!@pm5z+)(!xlrpzqvn*c96rv6*',
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = [
    'hamlet-staging.zooniverse.org',
    'hamlet.zooniverse.org',
    'hamlet-staging.azure.zooniverse.org',
]

if DEBUG:
    ALLOWED_HOSTS.append('localhost')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'social_django',
    'exports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hamlet.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR + '/templates/',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hamlet.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'hamlet'),
        'USER': os.environ.get('DB_USER', 'hamlet'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'hamlet'),
        'HOST': os.environ.get('DB_HOST', 'postgres'),
        'PORT': os.environ.get('DB_PORT', 5432),
        'OPTIONS': {'sslmode': os.environ.get('DB_SSL_MODE', 'prefer')},
    }
}

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = (
    'hamlet.zooniverse_auth.ZooniverseOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.getenv('STATIC_ROOT', os.path.join(BASE_DIR, 'hamlet', 'static'))
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

if not DEBUG:
    SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

SOCIAL_AUTH_ZOONIVERSE_KEY = os.environ.get(
    'PANOPTES_APPLICATION_ID',
    '',
)
SOCIAL_AUTH_ZOONIVERSE_SECRET = os.environ.get(
    'PANOPTES_SECRET',
    '',
)

# set the session length to be the same as the social auth token
# https://python-social-auth.readthedocs.io/en/latest/configuration/settings.html
SOCIAL_AUTH_SESSION_EXPIRATION = True

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
    },
}

REDIS_URI = os.environ.get('REDIS_URI', 'redis://redis')

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', None)
AWS_STORAGE_BUCKET_NAME = os.environ.get(
    'AWS_STORAGE_BUCKET_NAME',
    'zooniverse-hamlet',
)
AWS_DEFAULT_ACL = None
AWS_LOCATION = '{}/'.format(os.environ.get('DJANGO_ENV', 'development'))
AWS_S3_OBJECT_PARAMETERS = {
    'ContentDisposition': 'attachment',
}

TMP_STORAGE_PATH = os.environ.get(
    'TMP_STORAGE_PATH',
    os.path.join(BASE_DIR, 'tmp'),
)

CAESAR_URL = os.environ.get(
    'CAESAR_URL',
    'https://caesar.zooniverse.org',
)

ZOONIVERSE_API_ENDPOINT = os.getenv('ZOONIVERSE_API_ENDPOINT', None)

# Camera Traps ML service settings
SUBJECT_ASSISTANT_EXTERNAL_URL = os.environ.get('SUBJECT_ASSISTANT_EXTERNAL_URL', 'https://subject-assistant.zooniverse.org/#/tasks/')
SUBJECT_ASSISTANT_AZURE_ACCOUNT_NAME = os.environ.get('SUBJECT_ASSISTANT_AZURE_ACCOUNT_NAME')
SUBJECT_ASSISTANT_AZURE_ACCOUNT_KEY = os.environ.get('SUBJECT_ASSISTANT_AZURE_ACCOUNT_KEY')
SUBJECT_ASSISTANT_AZURE_CONTAINER_NAME = os.environ.get('SUBJECT_ASSISTANT_AZURE_CONTAINER_NAME')

# KaDE ML service settings
KADE_SUBJECT_ASSISTANT_EXTERNAL_URL = os.environ.get('KADE_SUBJECT_ASSISTANT_EXTERNAL_URL', 'https://subject-assistant.zooniverse.org')
KADE_SUBJECT_ASSISTANT_AZURE_ACCOUNT_NAME = os.environ.get('KADE_SUBJECT_ASSISTANT_AZURE_ACCOUNT_NAME')
KADE_SUBJECT_ASSISTANT_AZURE_ACCOUNT_KEY = os.environ.get('KADE_SUBJECT_ASSISTANT_AZURE_ACCOUNT_KEY')
KADE_SUBJECT_ASSISTANT_AZURE_CONTAINER_NAME = os.environ.get('KADE_SUBJECT_ASSISTANT_AZURE_CONTAINER_NAME')

