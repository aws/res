#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the 'License'). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

"""
Custom credential broker
This function is triggered by virtual desktop infrastructure (VDI) instances
to provide temporary credentials for mounting object storage.
"""

import logging
import json
import os
from .virtual_desktop_controller_server_db import VirtualDesktopControllerServerDB
from .virtual_desktop_controller_user_sessions_db import VirtualDesktopControllerUserSessionsDB
from .shared_storage_db import SharedStorageDB
from .utils import Utils

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CLUSTER_NAME = os.environ.get('CLUSTER_NAME')
MODULE_ID = os.environ.get('MODULE_ID')
READ_ONLY_ROLE_NAME_ARN = os.environ.get('READ_ONLY_ROLE_NAME_ARN')
READ_AND_WRITE_ROLE_NAME_ARN = os.environ.get('READ_AND_WRITE_ROLE_NAME_ARN')
OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX = os.environ.get('OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX')
OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX = os.environ.get('OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX')
OBJECT_STORAGE_NO_CUSTOM_PREFIX = os.environ.get('OBJECT_STORAGE_NO_CUSTOM_PREFIX')

vdc_server_db = VirtualDesktopControllerServerDB(CLUSTER_NAME, MODULE_ID, logger)
vdc_user_session_db = VirtualDesktopControllerUserSessionsDB(CLUSTER_NAME, MODULE_ID, logger)
shared_storage_db = SharedStorageDB(logger)


def handler(event, _):
    try:
        logger.info(f'event: {event}')
        request_context = event['requestContext']

        filesystem_name = Utils.get_filesystem_name_from_request_context(event)
        instance_id = Utils.get_instance_id_from_request_context(request_context)
        source_ip = Utils.get_source_ip_from_request_context(request_context)

        if not all([filesystem_name, instance_id, source_ip]):
            raise ValueError('Invalid input parameters in the request context')

        server_response = vdc_server_db.get_owner_id_and_session_id(instance_id)
        if not server_response:
            raise ValueError(f'Invalid instance, instance_id {instance_id} is not a VDI')

        owner_id, session_id = server_response.get("owner_id"), server_response.get("session_id")
        if not all([owner_id, session_id]):
            raise ValueError(f'Invalid instance, instance_id {instance_id} is not a VDI')

        project_id = vdc_user_session_db.get_project_id(owner_id, session_id)
        if not project_id:
            raise ValueError('Instance is not associated with a project or lost project tag')

        if not Utils.validate_instance_origin(instance_id, source_ip):
            raise ValueError(f'Invalid instance, instance_id {instance_id} credentials is not from the origin')

        object_storage_model = shared_storage_db.get_object_storage_model(filesystem_name)
        if not object_storage_model:
            raise ValueError(f'Filesystem {filesystem_name} does not exist')

        if project_id not in object_storage_model.get_projects():
            raise ValueError(f'Filesystem is not associated with project {project_id}')

        if not shared_storage_db.is_provider_s3(filesystem_name):
            raise ValueError(f'Filesystem {filesystem_name} is not associated with an S3 Bucket')

        read_only = shared_storage_db.get_object_storage_read_only(filesystem_name)
        bucket_arn = object_storage_model.get_bucket_arn()
        bucket_arn_without_prefix = Utils.extract_bucket_arn_without_prefix(bucket_arn)

        if not bucket_arn_without_prefix:
            raise ValueError(f'Invalid bucket arn {bucket_arn}')

        prefix = Utils.extract_prefix_from_bucket_arn(bucket_arn)
        if not read_only:
            custom_bucket_prefix = shared_storage_db.get_object_storage_custom_bucket_prefix(filesystem_name)
            append_prefix = {
                OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX: project_id,
                OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX: f'{project_id}/{owner_id}',
                OBJECT_STORAGE_NO_CUSTOM_PREFIX: '',
            }.get(custom_bucket_prefix, None)

            if append_prefix is None:
                raise ValueError(f'Unknown custom bucket prefix {custom_bucket_prefix}')

            prefix = f'{prefix.rstrip("/")}/{append_prefix}' if prefix else append_prefix

        role_arn = shared_storage_db.get_object_storage_iam_role_arn(filesystem_name) or (
            READ_ONLY_ROLE_NAME_ARN if read_only else READ_AND_WRITE_ROLE_NAME_ARN
        )

        credentials = Utils.get_temporary_credentials(
            role_arn=role_arn,
            role_session_name='S3-Mount-Temporary-Credentials',
            bucket_arn=bucket_arn_without_prefix,
            read_only=read_only,
            prefix=prefix
        )
        if credentials is None:
            raise ValueError('Unable to get temporary credentials')

        return {
            'statusCode': 200,
            'body': json.dumps(credentials)
        }

    except Exception as e:
        logger.exception(f'Error in getting custom credentials: {event}, error: {e}')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
