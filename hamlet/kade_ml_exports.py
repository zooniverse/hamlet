from azure.storage.blob import BlockBlobService, BlobPermissions
import json
import os
import tempfile
import requests
from datetime import datetime, timedelta

import django
# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hamlet.settings')
django.setup()

from django.conf import settings

from .zooniverse_auth import SocialPanoptes
from . import kade_service
from panoptes_client import SubjectSet


def subject_assistant_export_get_subjects_data(
    export,
    access_token,
):
    print('[Subject Assistant] Exporting to KaDE: get Subjects')

    # Keeps track of all data items that needs to written into the export JSON format.
    data = []

    # Retrieve all Subjects from a Subject Set
    with SocialPanoptes(bearer_token=access_token) as sp:
        subject_set = SubjectSet.find(export.subject_set_id)

        # Process each Subject
        for subject in subject_set.subjects:

            # Create a data item for each image URL in the Subject
            for frame_id, location in enumerate(subject.locations):
                image_url = list(location.values())[0]

                subject_information = {
                    'project_id': str(subject_set.links.project.id),
                    'subject_set_id': str(export.subject_set_id),
                    'subject_id': str(subject.id),
                    'frame_id': str(frame_id)
                }

                item = []
                item.append(image_url)
                # The subject's JSON information is stored as a string. Yes, really.
                item.append(json.dumps(subject_information))

                data.append(item)

    return data


def subject_assistant_export_to_create_export_file(data):

    print('[Subject Assistant] Exporting to KaDE: create file')

    # Write the data to a file
    source_filepath = ''
    try:
        # First create a temporary JSON file
        with tempfile.NamedTemporaryFile(
            'w+',
            encoding='utf-8',
            dir=settings.TMP_STORAGE_PATH,
            delete=False,
        ) as out_f:
            json.dump(data, out_f)
            out_f.flush()
            source_filepath = out_f.name

        return source_filepath

    except Exception as err:

        print('[ERROR] ', err)

        # Only cleanup the temporary file on error; otherwise it'll be cleaned up in the main function.
        try:
            if len(source_filepath) > 0:
                os.unlink(source_filepath)
        except OSError:
            pass

        raise err


def subject_assistant_export_to_shareable_blob_storage_location(
    source_filepath,
    target_filename,
):

    print('[Subject Assistant] Exporting to KaDE: upload to shareable blob storage location')

    shareable_file_url = ''

    try:
        block_blob_service = BlockBlobService(
            account_name=settings.KADE_SUBJECT_ASSISTANT_AZURE_ACCOUNT_NAME,
            account_key=settings.KADE_SUBJECT_ASSISTANT_AZURE_ACCOUNT_KEY)

        block_blob_service.create_blob_from_path(
            settings.KADE_SUBJECT_ASSISTANT_AZURE_CONTAINER_NAME, target_filename, source_filepath)

        blob_permissions = BlobPermissions(read=True)
        sas_expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        generated_sas = block_blob_service.generate_blob_shared_access_signature(
            container_name=settings.KADE_SUBJECT_ASSISTANT_AZURE_CONTAINER_NAME,
            blob_name=target_filename,
            permission=blob_permissions,
            expiry=sas_expiry
        )

        shareable_file_url = 'https://{}.blob.core.windows.net/{}/{}?{}'.format(
            settings.KADE_SUBJECT_ASSISTANT_AZURE_ACCOUNT_NAME,
            settings.KADE_SUBJECT_ASSISTANT_AZURE_CONTAINER_NAME,
            target_filename,
            generated_sas
        )

    except Exception as err:
        print('[ERROR] ', err)
        raise err

    return shareable_file_url


def subject_assistant_export_to_kade(shareable_file_url):

    print('[Subject Assistant] Exporting to KaDE: make request to KaDE Prediction API service')

    kade_job_id = None

    req_body = {
        'prediction_job': {
            'manifest_url': shareable_file_url
        }
    }

    try:
        # submit the manifest to the KaDE predictions API
        res = requests.post(
            kade_service.url(),
            json=req_body,
            headers=kade_service.headers(),
            auth=(kade_service.basic_auth_username(),
                  kade_service.basic_auth_password()),
            timeout=30
        )
        res.raise_for_status()

        response_json = res.json()
        kade_job_id = response_json['id']

    except Exception as err:
        print('[ERROR] ', err)
        raise err

    return kade_job_id

