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

from exports.models import MLSubjectAssistantExport
from .zooniverse_auth import SocialPanoptes
from panoptes_client import SubjectSet


def ml_subject_assistant_export_to_microsoft_pt1_get_subjects_data(
    export_id,
    access_token,
):
    print('[Subject Assistant] Exporting to Microsoft 1/4: get Subjects')

    export = MLSubjectAssistantExport.objects.get(pk=export_id)
    # Keeps track of all data items that needs to written into a Microsoft-friendly JSON format.
    data = []

    # Retrieve all Subjects from a Subject Set
    with SocialPanoptes(bearer_token=access_token) as p:
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


def ml_subject_assistant_export_to_microsoft_pt2_create_file(export_id, data, target_filename):

    print('[Subject Assistant] Exporting to Microsoft 2/4: create file')

    export = MLSubjectAssistantExport.objects.get(pk=export_id)

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


def ml_subject_assistant_export_to_microsoft_pt3_create_shareable_azure_blob(
    source_filepath,
    target_filename,
):

    print('[Subject Assistant] Exporting to Microsoft 3/4: create shareable Azure blob')

    shareable_file_url = ''

    try:
        block_blob_service = BlockBlobService(
            account_name=settings.SUBJECT_ASSISTANT_AZURE_ACCOUNT_NAME, account_key=settings.SUBJECT_ASSISTANT_AZURE_ACCOUNT_KEY)

        created_blob = block_blob_service.create_blob_from_path(
            settings.SUBJECT_ASSISTANT_AZURE_CONTAINER_NAME, target_filename, source_filepath)

        blob_permissions = BlobPermissions(read=True)
        sas_expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        generated_sas = block_blob_service.generate_blob_shared_access_signature(
            container_name=settings.SUBJECT_ASSISTANT_AZURE_CONTAINER_NAME,
            blob_name=target_filename,
            permission=blob_permissions,
            expiry=sas_expiry
        )

        shareable_file_url = 'https://{}.blob.core.windows.net/{}/{}?{}'.format(
            settings.SUBJECT_ASSISTANT_AZURE_ACCOUNT_NAME,
            settings.SUBJECT_ASSISTANT_AZURE_CONTAINER_NAME,
            target_filename,
            generated_sas
        )

    except Exception as err:
        print('[ERROR] ', err)
        raise err

    return shareable_file_url


def ml_subject_assistant_export_to_microsoft_pt4_make_ml_request(shareable_file_url):

    print('[Subject Assistant] Exporting to Microsoft 4/4: make request to Microsoft')

    ml_task_uuid = None

    try:
        # the secret caller id used to identify ourselves via an allowlist on the hosted service
        ml_service_caller_id = os.environ.get(
            'SUBJECT_ASSISTANT_ML_SERVICE_CALLER_ID')
        # default to the externally hosted camera traps API service
        ml_service_url = os.environ.get('SUBJECT_ASSISTANT_ML_SERVICE_URL')

        # use Zooniverse k8s hosted camera traps API service if available
        # this env var is automatically setup by our K8s system via the Camera Traps Api service definition
        # thus if this is present, we're running in the Zooniverse K8s cluster!
        # https://github.com/zooniverse/CameraTraps/tree/zooniverse-deployment
        camera_traps_api_host = os.getenv('CAMERA_TRAPS_API_SERVICE_HOST')
        if camera_traps_api_host:
          camera_traps_api_host_path = os.getenv(
              'CAMERA_TRAPS_API_SERVICE_HOST_PATH', '/v4/camera-trap/detection-batch'
          )
          ml_service_url = 'http://' + camera_traps_api_host + camera_traps_api_host_path

        req_url = ml_service_url + '/request_detections'
        req_body = {
            'images_requested_json_sas': shareable_file_url,
            'use_url': 'true',
            # Note: this field may be optional
            'request_name': 'zooniverse-subject-assistant',
            'caller': ml_service_caller_id
        }

        res = requests.post(
            req_url,
            json=req_body,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        res.raise_for_status()

        response_json = res.json()
        ml_task_uuid = response_json['request_id']

    except Exception as err:
        print('[ERROR] ', err)
        raise err

    return ml_task_uuid

