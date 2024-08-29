#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from ideadatamodel import (
    exceptions, constants
)
from ideadatamodel.aws.model import AWSTag
from ideadatamodel.shared_filesystem.shared_filesystem_api import OnboardS3BucketRequest
from ideasdk.aws import AWSUtil
from ideasdk.context import SocaContext
from ideasdk.utils import Utils, ApiUtils


class ObjectStorageService:

    def __init__(self, context: SocaContext):
        self._context = context

    def build_config_for_s3_bucket(self, request: OnboardS3BucketRequest):

        # Used to remain consistent with rest of filesystems
        filesystem_name = self._generate_filesystem_name(request.bucket_arn)

        bucket_config = {
            filesystem_name: {
                "title": request.object_storage_title,
                "provider": constants.STORAGE_PROVIDER_S3_BUCKET,
                "projects": [],
                "scope": ["project"],
                "mount_dir": request.mount_directory,
                constants.STORAGE_PROVIDER_S3_BUCKET: {
                    "read_only": request.read_only,
                    "bucket_arn": request.bucket_arn,
                }
            }
        }

        if request.projects:
            bucket_config[filesystem_name]["projects"] = request.projects

        if not request.read_only:
            bucket_config[filesystem_name][constants.STORAGE_PROVIDER_S3_BUCKET]["custom_bucket_prefix"] = request.custom_bucket_prefix

        if request.iam_role_arn:
            bucket_config[filesystem_name][constants.STORAGE_PROVIDER_S3_BUCKET]["iam_role_arn"] = request.iam_role_arn

        return {
            "config": bucket_config,
            "filesystem_name": filesystem_name
        }

    def validate_onboard_object_storage_request(self, request: OnboardS3BucketRequest):
        if Utils.is_empty(request):
            raise exceptions.invalid_params('missing request')
        elif Utils.is_empty(request.object_storage_title):
            raise exceptions.invalid_params('missing object_storage_title')
        elif Utils.is_empty(request.bucket_arn):
            raise exceptions.invalid_params('missing bucket_arn')
        elif Utils.is_empty(request.mount_directory):
            raise exceptions.invalid_params('missing mount_directory')
        elif Utils.is_empty(request.read_only):
            raise exceptions.invalid_params('missing read_only')

        ApiUtils.validate_input(request.mount_directory,
                                constants.MOUNT_DIRECTORY_REGEX,
                                constants.MOUNT_DIRECTORY_ERROR_MESSAGE)

        if not request.read_only and Utils.is_empty(request.custom_bucket_prefix):
            raise exceptions.invalid_params('read and write access enabled, missing custom_bucket_prefix')

        if not AWSUtil.is_valid_s3_bucket_arn(request.bucket_arn):
            raise exceptions.invalid_params(constants.S3_BUCKET_ARN_ERROR_MESSAGE)

        s3_bucket_iam_role_filter_tag = AWSTag(Key=constants.S3_BUCKET_IAM_ROLE_RESOURCE_TAG_KEY, Value=constants.S3_BUCKET_IAM_ROLE_RESOURCE_TAG_VALUE)
        if Utils.is_not_empty(request.iam_role_arn):
            if not AWSUtil.is_valid_iam_role_arn(request.iam_role_arn):
                raise exceptions.invalid_params(constants.IAM_ROLE_ARN_ERROR_MESSAGE)
            if not self._context.aws_util().does_iam_role_exist(role_arn=request.iam_role_arn, filter_tags=[s3_bucket_iam_role_filter_tag]):
                raise exceptions.invalid_params(constants.S3_BUCKET_IAM_ROLE_ERROR_MESSAGE)
        
        if Utils.is_not_empty(request.projects):
            for project_name in request.projects:
                ApiUtils.validate_input(project_name,
                                constants.PROJECT_ID_REGEX,
                                constants.PROJECT_ID_ERROR_MESSAGE)

    @staticmethod
    def _generate_filesystem_name(bucket_arn):
        bucket_name = AWSUtil.get_bucket_name_from_bucket_arn(bucket_arn)
        return f'{bucket_name}-{Utils.short_uuid()}'
