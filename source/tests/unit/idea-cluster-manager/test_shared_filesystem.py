#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

"""
Test Cases for SharedFilesystemService
"""

from unittest.mock import MagicMock

import botocore.exceptions
import pytest
import shortuuid
from _pytest.monkeypatch import MonkeyPatch
from ideaclustermanager import AppContext
from ideasdk.aws import AwsClientProvider

from ideadatamodel import (
    AddFileSystemToProjectRequest,
    FileSystem,
    ListOnboardedFileSystemsRequest,
    ListOnboardedFileSystemsResult,
    OnboardLUSTREFileSystemRequest,
    OnboardS3BucketRequest,
    RemoveFileSystemFromProjectRequest,
    RemoveFileSystemRequest,
    SocaAnyPayload,
    SocaFilter,
    UpdateFileSystemRequest,
    constants,
    errorcodes,
    exceptions,
)

MOCK_S3_BUCKET_FILESYSTEM_NAME = "bucket-name-uuid"

MOCK_S3_BUCKET_BUCKET_ARN = "arn:aws:s3:::example-bucket"

MOCK_PROJECT_NAME = "dummy_project"
MOCK_S3_BUCKET_CONFIG = {
    "s3_bucket": {
        "read_only": True,
        "bucket_arn": MOCK_S3_BUCKET_BUCKET_ARN,
    },
    "mount_dir": "/s3-bucket",
    "provider": "s3_bucket",
    "scope": ["project"],
    "projects": [MOCK_PROJECT_NAME],
    "title": "s3-bucket-1",
}


def test_shared_filesystem_onboard_lustre_file_system_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    """
    onboard an FSx Lustre file system
    """

    mock_ec2 = SocaAnyPayload()
    mock_ec2.describe_subnets = MagicMock(
        return_value={"Subnets": [{"VpcId": "vpc_id"}]}
    )

    monkeypatch.setattr(AwsClientProvider, "ec2", lambda *_: mock_ec2)

    def _get_config_entry_mock(key: str):
        if key == "cluster.network.vpc_id":
            return {"value": "vpc_id"}
        else:
            return MagicMock()

    monkeypatch.setattr(
        context.shared_filesystem.config.db, "get_config_entry", _get_config_entry_mock
    )

    request = OnboardLUSTREFileSystemRequest(
        filesystem_name="lustre_name",
        filesystem_title="lustre_title",
        filesystem_id="lustre_filesystem_id",
        mount_directory="/lustre",
    )
    context.shared_filesystem.onboard_lustre_filesystem(request)


def test_shared_filesystem_onboard_lustre_file_system_missing_required_field_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    """
    onboard an FSx Lustre file system without providing required fields
    """
    request = OnboardLUSTREFileSystemRequest(
        filesystem_name="",
        filesystem_title="",
        filesystem_id="",
        mount_directory="/lustre",
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_lustre_filesystem(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "needed parameters cannot be empty" in exc_info.value.message


def test_shared_filesystem_onboard_lustre_file_system_already_exists_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    """
    onboard an FSx Lustre file system with a file system name that already exists in RES
    """
    monkeypatch.setattr(
        context.shared_filesystem, "get_filesystem", lambda *_: "lustre_name"
    )

    request = OnboardLUSTREFileSystemRequest(
        filesystem_name="lustre_name",
        filesystem_title="lustre_title",
        filesystem_id="lustre_filesystem_id",
        mount_directory="/lustre",
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_lustre_filesystem(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "lustre_name already exists" in exc_info.value.message


def test_shared_filesystem_onboard_lustre_file_system_not_present_in_vpc_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    """
    onboard an FSx Lustre file system that does not present in the VPC
    """
    mock_ec2 = SocaAnyPayload()
    mock_ec2.describe_subnets = MagicMock(
        return_value={"Subnets": [{"VpcId": "other_vpc_id"}]}
    )

    monkeypatch.setattr(AwsClientProvider, "ec2", lambda *_: mock_ec2)

    def _get_config_entry_mock(key: str):
        if key == "cluster.network.vpc_id":
            return {"value": "vpc_id"}
        else:
            return MagicMock()

    monkeypatch.setattr(
        context.shared_filesystem.config.db, "get_config_entry", _get_config_entry_mock
    )

    request = OnboardLUSTREFileSystemRequest(
        filesystem_name="lustre_name",
        filesystem_title="lustre_title",
        filesystem_id="lustre_filesystem_id",
        mount_directory="/lustre",
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_lustre_filesystem(request)
    assert exc_info.value.error_code == errorcodes.FILESYSTEM_NOT_IN_VPC
    assert (
        "lustre_filesystem_id not part of the env's VPC thus not accessible"
        in exc_info.value.message
    )


def test_shared_filesystem_onboard_lustre_file_system_already_onboarded_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    """
    onboard an FSx Lustre file system that has already been onboarded
    """
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_lustre_file_system",
                    storage={
                        "provider": "fsx_lustre",
                        "fsx_lustre": {"file_system_id": "lustre_filesystem_id"},
                    },
                )
            ],
        ),
    )

    request = OnboardLUSTREFileSystemRequest(
        filesystem_name="lustre_name",
        filesystem_title="lustre_title",
        filesystem_id="lustre_filesystem_id",
        mount_directory="/lustre",
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_lustre_filesystem(request)
    assert exc_info.value.error_code == errorcodes.FILESYSTEM_ALREADY_ONBOARDED
    assert "lustre_filesystem_id has already been onboarded" in exc_info.value.message


def test_shared_filesystem_onboard_s3_bucket_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    mock_uuid = "mock_uuid"
    # Mock the uuid.uuid4 function
    monkeypatch.setattr(shortuuid, "uuid", lambda: mock_uuid)
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(listing=[]),
    )
    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=True,
        mount_directory="/bucket",
        projects=["dummy-proj"],
    )
    # Ensure there are no exceptions being thrown
    context.shared_filesystem.onboard_s3_bucket(request)
    filesystem_name = context.shared_filesystem.onboard_s3_bucket(request)
    assert filesystem_name == f"example-bucket-{mock_uuid}"


def test_shared_filesystem_onboard_s3_bucket_no_mount_point_collision_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    mock_uuid = "mock_uuid"
    # Mock the uuid.uuid4 function
    monkeypatch.setattr(shortuuid, "uuid", lambda: mock_uuid)
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket_1",
                    storage={
                        "provider": "s3_bucket",
                        "projects": ["dummy-proj-1"],
                        "mount_dir": "/bucket-1",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::onboarded-s3-bucket-1/prefix"
                        },
                    },
                ),
            ],
        ),
    )
    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=True,
        mount_directory="/example-bucket",
        projects=["dummy-proj-1"],
    )
    # Ensure there are no exceptions being thrown
    filesystem_name = context.shared_filesystem.onboard_s3_bucket(request)
    assert filesystem_name == f"example-bucket-{mock_uuid}"


def test_shared_filesystem_onboard_s3_bucket_invalid_bucket_arn_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="invalid_arn",
        read_only=True,
        mount_directory="/bucket",
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_s3_bucket(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.S3_BUCKET_ARN_ERROR_MESSAGE in exc_info.value.message


def test_shared_filesystem_onboard_s3_bucket_non_existent_iam_role_arn_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    mock_iam = SocaAnyPayload()
    mock_iam.get_role = MagicMock()
    mock_iam.get_role.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "NoSuchEntityException", "Message": "MockedErrorMessage"}},
        "operation_name",
    )
    monkeypatch.setattr(AwsClientProvider, "iam", lambda *_: mock_iam)

    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=True,
        mount_directory="/bucket",
        iam_role_arn="arn:aws:iam::123456789012:role/MyIAMRole-Does-Not-Exist",
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_s3_bucket(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.S3_BUCKET_IAM_ROLE_ERROR_MESSAGE in exc_info.value.message


def test_shared_filesystem_onboard_s3_bucket_invalid_iam_role_arn_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=True,
        mount_directory="/bucket",
        iam_role_arn="invalid IAM role ARN",
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_s3_bucket(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.IAM_ROLE_ARN_ERROR_MESSAGE in exc_info.value.message


def test_shared_filesystem_onboard_s3_bucket_valid_iam_role_arn_invalid_tags_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    mock_iam = SocaAnyPayload()
    mock_iam.get_role = MagicMock(
        return_value={
            "Role": {
                "Tags": [
                    {
                        "Key": constants.S3_BUCKET_IAM_ROLE_RESOURCE_TAG_KEY,
                        "Value": "invalid_tag",
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(AwsClientProvider, "iam", lambda *_: mock_iam)

    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=True,
        mount_directory="/bucket",
        iam_role_arn="arn:aws:iam::123456789012:role/MyIAMRole",
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_s3_bucket(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.S3_BUCKET_IAM_ROLE_ERROR_MESSAGE in exc_info.value.message


def test_shared_filesystem_onboard_s3_bucket_valid_iam_role_arn_valid_tags_succeeds(
    context: AppContext, monkeypatch: MonkeyPatch
):
    mock_iam = SocaAnyPayload()
    mock_iam.get_role = MagicMock(
        return_value={
            "Role": {
                "Tags": [
                    {
                        "Key": constants.S3_BUCKET_IAM_ROLE_RESOURCE_TAG_KEY,
                        "Value": constants.S3_BUCKET_IAM_ROLE_RESOURCE_TAG_VALUE,
                    }
                ]
            }
        }
    )

    monkeypatch.setattr(AwsClientProvider, "iam", lambda *_: mock_iam)
    mock_uuid = "mock_uuid"
    # Mock the uuid.uuid4 function
    monkeypatch.setattr(shortuuid, "uuid", lambda: mock_uuid)

    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(listing=[]),
    )

    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=True,
        mount_directory="/bucket",
        iam_role_arn="arn:aws:iam::123456789012:role/MyIAMRole",
    )
    # Ensure there are no exceptions being thrown
    context.shared_filesystem.onboard_s3_bucket(request)
    filesystem_name = context.shared_filesystem.onboard_s3_bucket(request)
    assert filesystem_name == f"example-bucket-{mock_uuid}"


def test_shared_filesystem_onboard_s3_bucket_valid_iam_role_arn_with_a_prefix_valid_tags_succeeds(
    context: AppContext, monkeypatch: MonkeyPatch
):
    mock_iam = SocaAnyPayload()
    mock_iam.get_role = MagicMock(
        return_value={
            "Role": {
                "Tags": [
                    {
                        "Key": constants.S3_BUCKET_IAM_ROLE_RESOURCE_TAG_KEY,
                        "Value": constants.S3_BUCKET_IAM_ROLE_RESOURCE_TAG_VALUE,
                    }
                ]
            }
        }
    )

    monkeypatch.setattr(AwsClientProvider, "iam", lambda *_: mock_iam)
    mock_uuid = "mock_uuid"
    # Mock the uuid.uuid4 function
    monkeypatch.setattr(shortuuid, "uuid", lambda: mock_uuid)

    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(listing=[]),
    )

    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=True,
        mount_directory="/bucket",
        iam_role_arn="arn:aws:iam::123456789012:role/MyPrefix/MyIAMRole",
    )
    # Ensure there are no exceptions being thrown
    context.shared_filesystem.onboard_s3_bucket(request)
    filesystem_name = context.shared_filesystem.onboard_s3_bucket(request)
    assert filesystem_name == f"example-bucket-{mock_uuid}"


def test_shared_filesystem_onboard_s3_bucket_invalid_projects_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=True,
        mount_directory="/bucket",
        projects=["INVALID-PROJECT"],
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_s3_bucket(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.PROJECT_ID_ERROR_MESSAGE in exc_info.value.message


def test_shared_filesystem_onboard_s3_bucket_mount_point_collision_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket_1",
                    storage={
                        "provider": "s3_bucket",
                        "projects": ["dummy-proj-1"],
                        "mount_dir": "/bucket-1",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::onboarded-s3-bucket-1/prefix"
                        },
                    },
                ),
                FileSystem(
                    name="onboarded_s3_bucket_2",
                    storage={
                        "provider": "s3_bucket",
                        "projects": ["dummy-proj-1"],
                        "mount_dir": "/bucket-2",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::onboarded-s3-bucket-2/prefix"
                        },
                    },
                ),
            ],
        ),
    )
    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=True,
        mount_directory="/bucket-1",
        projects=["dummy-proj-1"],
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_s3_bucket(request)
    assert exc_info.value.error_code == errorcodes.FILESYSTEM_MOUNT_POINT_COLLISION
    assert (
        f"Mount point of {request.mount_directory} is already used in project {request.projects[0]}"
        in exc_info.value.message
    )


def test_shared_filesystem_onboard_s3_bucket_with_read_write_access_and_no_custom_bucket_prefix_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=False,
        mount_directory="/bucket",
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_s3_bucket(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        "read and write access enabled, missing custom_bucket_prefix"
        in exc_info.value.message
    )


def test_shared_filesystem_onboard_s3_bucket_with_read_write_access_and_custom_bucket_prefix_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    mock_uuid = "mock_uuid"
    # Mock the uuid.uuid4 function
    monkeypatch.setattr(shortuuid, "uuid", lambda: mock_uuid)

    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(listing=[]),
    )

    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=False,
        custom_bucket_prefix="PROJECT_NAME_AND_USERNAME_PREFIX",
        mount_directory="/bucket",
    )

    # Ensure there are no exceptions being thrown
    filesystem_name = context.shared_filesystem.onboard_s3_bucket(request)
    assert filesystem_name == f"example-bucket-{mock_uuid}"


def test_shared_filesystem_onboard_s3_bucket_bucket_arn_already_onboarded_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket",
                    storage={
                        "provider": "s3_bucket",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::example-bucket/prefix"
                        },
                    },
                )
            ],
        ),
    )
    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=True,
        mount_directory="/bucket",
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_s3_bucket(request)
    assert exc_info.value.error_code == errorcodes.FILESYSTEM_ALREADY_ONBOARDED
    assert (
        "arn:aws:s3:::example-bucket/prefix has already been onboarded"
        in exc_info.value.message
    )


def test_shared_filesystem_onboard_s3_bucket_bucket_arn_with_incorrect_mount_dir_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    request = OnboardS3BucketRequest(
        object_storage_title="s3_bucket_title",
        bucket_arn="arn:aws:s3:::example-bucket/prefix",
        read_only=True,
        mount_directory="invalid",
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.onboard_s3_bucket(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.MOUNT_DIRECTORY_ERROR_MESSAGE in exc_info.value.message


def test_shared_filesystem_add_filesystem_to_project_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name=MOCK_S3_BUCKET_FILESYSTEM_NAME, storage=MOCK_S3_BUCKET_CONFIG
                )
            ],
        ),
    )

    request = AddFileSystemToProjectRequest(
        filesystem_name=MOCK_S3_BUCKET_FILESYSTEM_NAME, project_name="example_project"
    )
    # No return value, ensure there were no errors thrown
    context.shared_filesystem.add_filesystem_to_project(request)


def test_shared_filesystem_add_filesystem_to_project_invalid_filesystem_fails(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name=MOCK_S3_BUCKET_FILESYSTEM_NAME, storage=MOCK_S3_BUCKET_CONFIG
                )
            ],
        ),
    )

    request = AddFileSystemToProjectRequest(
        filesystem_name="wrong_filesystem", project_name="example_project"
    )
    # No return value, ensure there were no errors thrown
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.add_filesystem_to_project(request)
    assert exc_info.value.error_code == errorcodes.FILESYSTEM_NOT_FOUND
    assert "could not find filesystem wrong_filesystem" in exc_info.value.message


def test_shared_filesystem_add_filesystem_to_project_project_already_attached_succeeds(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name=MOCK_S3_BUCKET_FILESYSTEM_NAME, storage=MOCK_S3_BUCKET_CONFIG
                )
            ],
        ),
    )

    request = AddFileSystemToProjectRequest(
        filesystem_name=MOCK_S3_BUCKET_FILESYSTEM_NAME, project_name=MOCK_PROJECT_NAME
    )
    # No return value, ensure there were no errors thrown
    context.shared_filesystem.add_filesystem_to_project(request)


def test_shared_filesystem_add_filesystem_to_project_project_invalid_params_fails(
    context: AppContext, monkeypatch: MonkeyPatch
):
    def verify_invalid_scenario(
        invalid_request: AddFileSystemToProjectRequest, error_message: str
    ):
        with pytest.raises(exceptions.SocaException) as exc_info:
            context.shared_filesystem.add_filesystem_to_project(invalid_request)
        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert error_message in exc_info.value.message

    verify_invalid_scenario(
        invalid_request=AddFileSystemToProjectRequest(),
        error_message="filesystem_name is required",
    )

    verify_invalid_scenario(
        invalid_request=AddFileSystemToProjectRequest(
            filesystem_name=MOCK_S3_BUCKET_FILESYSTEM_NAME
        ),
        error_message="project_name is required",
    )


def test_shared_filesystem_remove_filesystem_from_project_invalid_params_fails(
    context: AppContext, monkeypatch: MonkeyPatch
):
    def verify_invalid_scenario(
        invalid_request: RemoveFileSystemFromProjectRequest, error_message: str
    ):
        with pytest.raises(exceptions.SocaException) as exc_info:
            context.shared_filesystem.remove_filesystem_from_project(invalid_request)
        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert error_message in exc_info.value.message

    verify_invalid_scenario(
        invalid_request=RemoveFileSystemFromProjectRequest(),
        error_message="filesystem_name is required",
    )

    verify_invalid_scenario(
        invalid_request=RemoveFileSystemFromProjectRequest(
            filesystem_name=MOCK_S3_BUCKET_FILESYSTEM_NAME
        ),
        error_message="project_name is required",
    )


def test_shared_filesystem_remove_filesystem_from_project_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name=MOCK_S3_BUCKET_FILESYSTEM_NAME, storage=MOCK_S3_BUCKET_CONFIG
                )
            ],
        ),
    )

    request = RemoveFileSystemFromProjectRequest(
        filesystem_name=MOCK_S3_BUCKET_FILESYSTEM_NAME, project_name=MOCK_PROJECT_NAME
    )
    # No return value, ensure there were no errors thrown
    context.shared_filesystem.remove_filesystem_from_project(request)


def test_shared_filesystem_remove_filesystem_from_project_invalid_filesystem_fails(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name=MOCK_S3_BUCKET_FILESYSTEM_NAME, storage=MOCK_S3_BUCKET_CONFIG
                )
            ],
        ),
    )

    request = RemoveFileSystemFromProjectRequest(
        filesystem_name="wrong_filesystem", project_name=MOCK_PROJECT_NAME
    )
    # No return value, ensure there were no errors thrown
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.remove_filesystem_from_project(request)
    assert exc_info.value.error_code == errorcodes.FILESYSTEM_NOT_FOUND
    assert "could not find filesystem wrong_filesystem" in exc_info.value.message


def get_test_file_systems(areOnboardedFileSystems: bool):
    file_systems = {
        "internal": {
            "title": "Shared Storage - Internal",
            "provider": "efs",
            "scope": ["cluster"],
            "mount_dir": "/internal",
            "efs": {},
        },
        "home": {
            "title": "Shared Storage - Home",
            "provider": "efs",
            "scope": ["cluster"],
            "mount_dir": "/home",
            "efs": {},
        },
    }
    if areOnboardedFileSystems:
        file_systems.update(
            {
                "efs_name": {
                    "title": "efs_title",
                    "provider": "efs",
                    "projects": [],
                    "scope": ["project"],
                    "mount_dir": "/efs",
                    "efs": {},
                },
                "fsx_lustre_name": {
                    "title": "fsx_lustre_title",
                    "provider": "fsx_lustre",
                    "projects": [],
                    "scope": ["project"],
                    "mount_dir": "/fsx_lustre",
                    "fsx_lustre": {},
                },
                "fsx_netapp_ontap_name": {
                    "title": "fsx_netapp_ontap_title",
                    "provider": "fsx_netapp_ontap",
                    "projects": [],
                    "scope": ["project"],
                    "mount_dir": "/fsx_netapp_ontap",
                    "fsx_netapp_ontap": {},
                },
                "s3_bucket_id": {
                    "title": "s3_bucket_title",
                    "provider": "s3_bucket",
                    "projects": [],
                    "scope": ["project"],
                    "mount_dir": "/bucket",
                    "s3_bucket": {},
                },
            }
        )
    return file_systems


def test_shared_filesystem_list_onboarded_file_systems_none_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem.config.get_config(constants.MODULE_SHARED_STORAGE),
        "as_plain_ordered_dict",
        lambda *_: get_test_file_systems(False),
    )
    request = ListOnboardedFileSystemsRequest()
    result = context.shared_filesystem.list_onboarded_file_systems(request)

    assert len(result.listing) == 0


def test_shared_filesystem_list_onboarded_file_systems_no_filters_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem.config.get_config(constants.MODULE_SHARED_STORAGE),
        "as_plain_ordered_dict",
        lambda *_: get_test_file_systems(True),
    )
    request = ListOnboardedFileSystemsRequest()
    result = context.shared_filesystem.list_onboarded_file_systems(request)

    assert len(result.listing) == 4
    assert all("projects" in fs.storage.keys() for fs in result.listing)
    for provider in [
        constants.STORAGE_PROVIDER_EFS,
        constants.STORAGE_PROVIDER_FSX_LUSTRE,
        constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
        constants.STORAGE_PROVIDER_S3_BUCKET,
    ]:
        assert any(fs.storage["title"] == f"{provider}_title" for fs in result.listing)
        assert any(fs.storage["provider"] == provider for fs in result.listing)


def test_shared_filesystem_list_onboarded_file_systems_filter_by_title_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem.config.get_config(constants.MODULE_SHARED_STORAGE),
        "as_plain_ordered_dict",
        lambda *_: get_test_file_systems(True),
    )
    filter = [SocaFilter(key="title", starts_with="efs_")]
    request = ListOnboardedFileSystemsRequest(filters=filter)
    result = context.shared_filesystem.list_onboarded_file_systems(request)

    assert len(result.listing) == 1
    assert result.listing[0].storage["title"] == "efs_title"


def test_shared_filesystem_list_onboarded_file_systems_filter_by_provider_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem.config.get_config(constants.MODULE_SHARED_STORAGE),
        "as_plain_ordered_dict",
        lambda *_: get_test_file_systems(True),
    )
    for provider in [
        constants.STORAGE_PROVIDER_EFS,
        constants.STORAGE_PROVIDER_FSX_LUSTRE,
        constants.STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
        constants.STORAGE_PROVIDER_S3_BUCKET,
    ]:
        filters = [SocaFilter(key="provider", eq=provider)]
        request = ListOnboardedFileSystemsRequest(filters=filters)
        result = context.shared_filesystem.list_onboarded_file_systems(request)

        assert len(result.listing) == 1
        assert all("projects" in fs.storage.keys() for fs in result.listing)
        assert all(fs.storage["provider"] == provider for fs in result.listing)


def test_shared_filesystem_list_onboarded_file_systems_filter_by_title_and_provider_no_record_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem.config.get_config(constants.MODULE_SHARED_STORAGE),
        "as_plain_ordered_dict",
        lambda *_: get_test_file_systems(True),
    )
    filter = [
        SocaFilter(key="title", starts_with="Unonboarded EFS File System"),
        SocaFilter(key="provider", eq=constants.STORAGE_PROVIDER_EFS),
    ]
    request = ListOnboardedFileSystemsRequest(filters=filter)
    result = context.shared_filesystem.list_onboarded_file_systems(request)

    assert len(result.listing) == 0


def test_shared_filesystem_list_onboarded_file_systems_filter_by_title_and_provider_with_record_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem.config.get_config(constants.MODULE_SHARED_STORAGE),
        "as_plain_ordered_dict",
        lambda *_: get_test_file_systems(True),
    )
    filter = [
        SocaFilter(key="title", starts_with="efs_title"),
        SocaFilter(key="provider", eq=constants.STORAGE_PROVIDER_EFS),
    ]
    request = ListOnboardedFileSystemsRequest(filters=filter)
    result = context.shared_filesystem.list_onboarded_file_systems(request)

    assert len(result.listing) == 1
    assert result.listing[0].storage["title"] == "efs_title"
    assert result.listing[0].storage["provider"] == constants.STORAGE_PROVIDER_EFS


def test_shared_filesystem_list_onboarded_file_systems_filter_by_invalid_title_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    file_system_provider_filter = [
        SocaFilter(key="title", starts_with="invalid title with #$!&() not allowed")
    ]
    request = ListOnboardedFileSystemsRequest(filters=file_system_provider_filter)

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.list_onboarded_file_systems(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        "Only use valid alphanumeric, hyphens (-), underscores (_), and spaces ( ) characters for the file system title."
        in exc_info.value.message
    )


def test_shared_filesystem_list_onboarded_file_systems_filter_by_invalid_provider_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    file_system_provider_filter = [SocaFilter(key="provider", eq="invalid_provider")]
    request = ListOnboardedFileSystemsRequest(filters=file_system_provider_filter)

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.list_onboarded_file_systems(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "Only use supported storage providers." in exc_info.value.message


def test_shared_filesystem_update_filesystems_to_project_mappings_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket",
                    storage={
                        "provider": "s3_bucket",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::example-bucket/prefix"
                        },
                        "mount_dir": "/bucket",
                    },
                )
            ],
        ),
    )
    filesystem_names = ["onboarded_s3_bucket"]
    project_name = "example_project"
    filesystem_succeeded = (
        context.shared_filesystem.update_filesystems_to_project_mappings(
            filesystem_names, project_name
        )
    )
    assert filesystem_succeeded == filesystem_names


def test_shared_filesystem_update_filesystems_to_project_mappings_empty_filesystem_names_succeeds(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket",
                    storage={
                        "provider": "s3_bucket",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::example-bucket/prefix"
                        },
                        "mount_dir": "/bucket",
                    },
                )
            ],
        ),
    )
    filesystem_names = []
    project_name = "example_project"
    filesystem_succeeded = (
        context.shared_filesystem.update_filesystems_to_project_mappings(
            filesystem_names, project_name
        )
    )
    assert filesystem_succeeded == filesystem_names


def test_shared_filesystem_update_filesystems_to_project_mappings_empty_filesystem_names_and_cleanup_succeeds(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket",
                    storage={
                        "provider": "s3_bucket",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::example-bucket/prefix"
                        },
                        "mount_dir": "/bucket",
                        "projects": ["example_project"],
                    },
                ),
                FileSystem(
                    name="onboarded_s3_bucket_2",
                    storage={
                        "provider": "s3_bucket",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::example-bucket/prefix"
                        },
                        "mount_dir": "/bucket-2",
                        "projects": ["example_project"],
                    },
                ),
            ],
        ),
    )
    filesystem_names = []
    project_name = "example_project"
    filesystem_succeeded = (
        context.shared_filesystem.update_filesystems_to_project_mappings(
            filesystem_names, project_name
        )
    )
    assert filesystem_succeeded == filesystem_names
    # Ensures no exceptions are thrown when _cleanup_filesystems_to_project_mappings is called in function.
    # Test filesystems are expected to detach from project.


def test_shared_filesystem_update_filesystems_to_project_mappings_filesystem_not_onboarded_fails(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket",
                    storage={
                        "provider": "s3_bucket",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::example-bucket/prefix"
                        },
                        "mount_dir": "/bucket",
                    },
                )
            ],
        ),
    )
    invalid_filesystem_name = "not_onboarded_s3_bucket"
    filesystem_names = ["onboarded_s3_bucket", invalid_filesystem_name]
    project_name = "example_project"
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.update_filesystems_to_project_mappings(
            filesystem_names, project_name
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        f"Filesystem {invalid_filesystem_name} is not valid" in exc_info.value.message
    )


def test_shared_filesystem_update_filesystems_to_project_mappings_duplicate_mount_dir_fails(
    context: AppContext, monkeypatch: MonkeyPatch
):
    mount_dir = "/bucket"
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket",
                    storage={
                        "provider": "s3_bucket",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::example-bucket/prefix"
                        },
                        "mount_dir": mount_dir,
                    },
                ),
                FileSystem(
                    name="onboarded_s3_bucket_2",
                    storage={
                        "provider": "s3_bucket",
                        "s3_bucket": {"bucket_arn": "arn:aws:s3:::example-bucket"},
                        "mount_dir": mount_dir,
                    },
                ),
            ],
        ),
    )
    filesystem_names = ["onboarded_s3_bucket", "onboarded_s3_bucket_2"]
    project_name = "example_project"
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.update_filesystems_to_project_mappings(
            filesystem_names, project_name
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        f"Duplicate filesystems with the mount directory {mount_dir}"
        in exc_info.value.message
    )


def test_shared_filesystem_update_filesystems_to_project_mappings_some_updates_fails_still_succeeds(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket",
                    storage={
                        "provider": "s3_bucket",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::example-bucket/prefix"
                        },
                        "mount_dir": "/bucket",
                    },
                ),
                FileSystem(
                    name="onboarded_s3_bucket_2",
                    storage={
                        "provider": "s3_bucket",
                        "s3_bucket": {"bucket_arn": "arn:aws:s3:::example-bucket"},
                        "mount_dir": "/bucket2",
                    },
                ),
            ],
        ),
    )

    successful_filesystem = "onboarded_s3_bucket"

    def _mock_update_filesystem_project_mapping(filesystem_name, project_name):
        if filesystem_name == successful_filesystem:
            return
        else:
            raise exceptions.general_exception("Unexpected error")

    monkeypatch.setattr(
        context.shared_filesystem,
        "update_filesystem_to_project_mapping",
        _mock_update_filesystem_project_mapping,
    )

    filesystem_names = ["onboarded_s3_bucket", "onboarded_s3_bucket_2"]
    project_name = "example_project"
    filesystems_succeeded = (
        context.shared_filesystem.update_filesystems_to_project_mappings(
            filesystem_names, project_name
        )
    )
    assert len(filesystems_succeeded) == 1
    assert filesystems_succeeded[0] == successful_filesystem


def test_shared_filesystem_update_s3_bucket_no_mount_point_collision_no_projects_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "get_filesystem",
        lambda *_: FileSystem(
            name="onboarded_s3_bucket_1",
            storage={
                "title": "My S3 Bucket 1",
                "provider": "s3_bucket",
                "projects": [],
                "mount_dir": "/bucket-1",
                "s3_bucket": {
                    "bucket_arn": "arn:aws:s3:::onboarded-s3-bucket-1/prefix"
                },
            },
        ),
    )
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket_2",
                    storage={
                        "title": "My S3 Bucket 2",
                        "provider": "s3_bucket",
                        "projects": [],
                        "mount_dir": "/bucket-2",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::onboarded-s3-bucket-2/prefix"
                        },
                    },
                ),
            ],
        ),
    )
    request = UpdateFileSystemRequest(
        filesystem_name="onboarded_s3_bucket_1",
        filesystem_title="My S3 Bucket 1 Updated",
        projects=[],
    )
    # Ensure there are no exceptions being thrown
    context.shared_filesystem.update_filesystem(request)


def test_shared_filesystem_update_s3_bucket_no_mount_point_collision_with_projects_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "get_filesystem",
        lambda *_: FileSystem(
            name="onboarded_s3_bucket_1",
            storage={
                "title": "My S3 Bucket 1",
                "provider": "s3_bucket",
                "projects": ["dummy-proj-1"],
                "mount_dir": "/bucket-1",
                "s3_bucket": {
                    "bucket_arn": "arn:aws:s3:::onboarded-s3-bucket-1/prefix"
                },
            },
        ),
    )
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket_2",
                    storage={
                        "title": "My S3 Bucket 2",
                        "provider": "s3_bucket",
                        "projects": ["dummy-proj-2"],
                        "mount_dir": "/bucket-2",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::onboarded-s3-bucket-2/prefix"
                        },
                    },
                ),
            ],
        ),
    )
    request = UpdateFileSystemRequest(
        filesystem_name="onboarded_s3_bucket_1",
        filesystem_title="My S3 Bucket 1 Updated",
        projects=["dummy-proj-2"],
    )
    # Ensure there are no exceptions being thrown
    context.shared_filesystem.update_filesystem(request)


def test_shared_filesystem_update_s3_bucket_empty_filesystem_name_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    request = UpdateFileSystemRequest(
        filesystem_name="",
        filesystem_title="My S3 Bucket 1 Updated",
        projects=[],
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.update_filesystem(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "missing filesystem_name" in exc_info.value.message


def test_shared_filesystem_onboard_s3_bucket_mount_point_collision_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "get_filesystem",
        lambda *_: FileSystem(
            name="onboarded_s3_bucket_1",
            storage={
                "title": "My S3 Bucket 1",
                "provider": "s3_bucket",
                "projects": ["dummy-proj-1"],
                "mount_dir": "/bucket",
                "s3_bucket": {
                    "bucket_arn": "arn:aws:s3:::onboarded-s3-bucket-1/prefix"
                },
            },
        ),
    )
    monkeypatch.setattr(
        context.shared_filesystem,
        "list_onboarded_file_systems",
        lambda *_: ListOnboardedFileSystemsResult(
            listing=[
                FileSystem(
                    name="onboarded_s3_bucket_2",
                    storage={
                        "title": "My S3 Bucket 2",
                        "provider": "s3_bucket",
                        "projects": ["dummy-proj-2"],
                        "mount_dir": "/bucket",
                        "s3_bucket": {
                            "bucket_arn": "arn:aws:s3:::onboarded-s3-bucket-2/prefix"
                        },
                    },
                ),
            ],
        ),
    )
    request = UpdateFileSystemRequest(
        filesystem_name="onboarded_s3_bucket_1",
        filesystem_title="My S3 Bucket 1 Updated",
        projects=["dummy-proj-2"],
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.update_filesystem(request)
    assert exc_info.value.error_code == errorcodes.FILESYSTEM_MOUNT_POINT_COLLISION
    assert (
        f"Mount point of /bucket is already used in project {request.projects[0]}"
        in exc_info.value.message
    )


def test_shared_filesystem_remove_filesystem_succeed(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "get_filesystem",
        lambda *_: FileSystem(
            name="onboarded_s3_bucket_1",
            storage={
                "title": "My S3 Bucket 1",
                "provider": "s3_bucket",
                "projects": [],
                "mount_dir": "/bucket",
                "s3_bucket": {
                    "bucket_arn": "arn:aws:s3:::onboarded-s3-bucket-1/prefix"
                },
            },
        ),
    )
    request = RemoveFileSystemRequest(
        filesystem_name="onboarded_s3_bucket_1",
    )
    # Ensure there are no exceptions being thrown
    context.shared_filesystem.remove_filesystem(request)


def test_shared_filesystem_remove_filesystem_empty_filesystem_name_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    request = RemoveFileSystemRequest(
        filesystem_name="",
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.remove_filesystem(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "missing filesystem_name" in exc_info.value.message


def test_shared_filesystem_remove_filesystem_with_attached_projects_fail(
    context: AppContext, monkeypatch: MonkeyPatch
):
    monkeypatch.setattr(
        context.shared_filesystem,
        "get_filesystem",
        lambda *_: FileSystem(
            name="onboarded_s3_bucket_1",
            storage={
                "title": "My S3 Bucket 1",
                "provider": "s3_bucket",
                "projects": ["dummy-proj-1"],
                "mount_dir": "/bucket",
                "s3_bucket": {
                    "bucket_arn": "arn:aws:s3:::onboarded-s3-bucket-1/prefix"
                },
            },
        ),
    )
    request = RemoveFileSystemRequest(
        filesystem_name="onboarded_s3_bucket_1",
    )
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.shared_filesystem.remove_filesystem(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        "My S3 Bucket 1 filesystem has attached projects: dummy-proj-1"
        in exc_info.value.message
    )
