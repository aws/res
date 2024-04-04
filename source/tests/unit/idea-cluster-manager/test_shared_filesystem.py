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

import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideaclustermanager import AppContext
from ideasdk.aws import AwsClientProvider

from ideadatamodel import (
    FileSystem,
    OnboardLUSTREFileSystemRequest,
    SocaAnyPayload,
    errorcodes,
    exceptions,
)


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
        "_list_shared_filesystems",
        lambda *_: [
            FileSystem(
                name="onboarded_lustre_file_system",
                storage={
                    "provider": "fsx_lustre",
                    "fsx_lustre": {"file_system_id": "lustre_filesystem_id"},
                },
            )
        ],
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
