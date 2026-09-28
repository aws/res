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
S3 mount point validation tests.

Verifies that an S3 bucket onboarded as a RES filesystem via mountpoint-s3:
1. Mounts correctly on a VDI after launch and supports read/write + read-only.
2. Persists across a VDI stop/start cycle.
"""

import logging
import os
import shlex
import uuid
from typing import Any, Generator, Optional

import boto3
import pytest

from ideadatamodel import (  # type: ignore
    ListOnboardedFileSystemsRequest,
    OnboardS3BucketRequest,
    Project,
    RemoveFileSystemFromProjectRequest,
    RemoveFileSystemRequest,
    SocaFilter,
    constants,
)
from ideadatamodel.shared_filesystem.shared_filesystem_api import (  # type: ignore
    CustomBucketPrefixTypes,
)
from tests.integration.framework.client.api_client import (
    ApiClient,
    BatchStartSessionRequestContent,
    BatchStopSessionRequestContent,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.session import session
from tests.integration.framework.fixtures.software_stack import software_stack
from tests.integration.framework.fixtures.users.admin import admin
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.model_utils import get_backend_model_class
from tests.integration.framework.utils.session_utils import wait_for_session_state
from tests.integration.framework.utils.vdi_command_utils import (
    command_succeeded,
    run_command,
)
from tests.integration.tests.smoke.config import AL2023_SOFTWARE_STACK

logger = logging.getLogger(__name__)

# Backend data-model classes
VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
VirtualDesktopSessionState = get_backend_model_class(
    "virtual_desktop_session_state", "VirtualDesktopSessionState"
)

# SSM parameter prefix where the TestingInfraStack writes S3 bucket info
SSM_PREFIX = "/res/testing-infra"
S3_RW_STORAGE_NAME = "integ-test-s3-rw-1"
S3_RO_STORAGE_NAME = "integ-test-s3-ro-1"
S3_PERSIST_STORAGE_NAME = "integ-test-s3-ro-2"

# Mount directories must match ^/[a-z0-9-]{3,18}$
S3_RW_MOUNT_DIR = "/s3-integ-rw"
S3_RO_MOUNT_DIR = "/s3-integ-ro"
S3_PERSIST_MOUNT_DIR = "/s3-integ-per"

_TEST_MARKER = "res-s3-mount-integ-test"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_test_bucket_name(environment_name: str, region: str, storage_name: str) -> str:
    ssm_client = boto3.client("ssm", region_name=region)
    param_name = f"{SSM_PREFIX}/{environment_name}/{storage_name}/BucketName"
    try:
        response = ssm_client.get_parameter(Name=param_name)
    except ssm_client.exceptions.ParameterNotFound:
        pytest.skip(
            f"S3 test infrastructure not deployed in this region "
            f"(SSM parameter {param_name} not found)"
        )
    return str(response["Parameter"]["Value"])


def _get_test_bucket_arn(bucket_name: str) -> str:
    return f"arn:aws:s3:::{bucket_name}"


def _list_s3_filesystems(client: ResClient) -> list:  # type: ignore[type-arg]
    """List all onboarded S3 filesystems."""
    s3_filter = SocaFilter(
        key=constants.FILE_SYSTEM_PROVIDER_KEY,
        eq=constants.STORAGE_PROVIDER_S3_BUCKET,
    )
    result = client.list_onboarded_file_systems(
        ListOnboardedFileSystemsRequest(filters=[s3_filter])
    )
    return result.listing or []


def _find_filesystem_name_by_bucket_arn(
    client: ResClient, bucket_arn: str
) -> Optional[str]:
    for fs in _list_s3_filesystems(client):
        if fs.get_filesystem_id() == bucket_arn:
            name: Optional[str] = fs.get_name()
            return name
    return None


def _remove_s3_filesystem(client: ResClient, bucket_arn: str) -> None:
    """Remove the onboarded S3 filesystem, detaching all projects first."""
    for fs in _list_s3_filesystems(client):
        if fs.get_filesystem_id() != bucket_arn:
            continue
        fs_name: Optional[str] = fs.get_name()
        if not fs_name:
            logger.warning(
                f"Filesystem for {bucket_arn} has no name — skipping removal"
            )
            return
        for proj in fs.get_projects() or []:
            client.remove_filesystem_from_project(
                RemoveFileSystemFromProjectRequest(
                    filesystem_name=fs_name,
                    project_name=proj,
                )
            )
        client.remove_filesystem(RemoveFileSystemRequest(filesystem_name=fs_name))
        return


def _cleanup_test_objects(bucket_name: str, region: str, prefix: str) -> None:
    s3_client = boto3.client("s3", region_name=region)
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        objects = page.get("Contents", [])
        if objects:
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={"Objects": [{"Key": obj["Key"]} for obj in objects]},
            )


def _stop_and_start_vdi(api_client: ApiClient, session: Any) -> Any:
    """Stop and start a VDI, returning the refreshed session in READY state."""
    minimal = VirtualDesktopSession(
        idea_session_id=session.idea_session_id,
        owner=session.owner,
        name=session.name,
        hibernation_enabled=False,
    )
    api_client.batch_stop_session(BatchStopSessionRequestContent(sessions=[minimal]))
    session = wait_for_session_state(
        api_client, session, VirtualDesktopSessionState.STOPPED
    )
    api_client.batch_start_session(BatchStartSessionRequestContent(sessions=[minimal]))
    session = wait_for_session_state(
        api_client, session, VirtualDesktopSessionState.READY
    )
    return session


# ---------------------------------------------------------------------------
# S3 filesystem fixtures — onboard before project creation, teardown after.
# Reference in project param as "fixture:s3_rw_filesystem" etc.
# ---------------------------------------------------------------------------


def _s3_filesystem_fixture(
    res_environment: ResEnvironment,
    environment_name: str,
    region: str,
    admin: ClientAuth,
    api_invoker_type: str,
    storage_name: str,
    mount_dir: str,
    read_only: bool,
) -> Generator[str, None, None]:
    """Shared implementation for S3 filesystem fixtures."""
    client = ResClient(res_environment, admin, api_invoker_type)
    bucket_name = _get_test_bucket_name(environment_name, region, storage_name)
    bucket_arn = _get_test_bucket_arn(bucket_name)

    _remove_s3_filesystem(client, bucket_arn)

    req = OnboardS3BucketRequest(
        object_storage_title=f"Integ Test S3 ({mount_dir})",
        bucket_arn=bucket_arn,
        read_only=read_only,
        mount_directory=mount_dir,
        projects=[],
        custom_bucket_prefix=(
            None if read_only else CustomBucketPrefixTypes.NoCustomPrefix
        ),
    )
    client.onboard_s3_bucket(req)

    fs_name = _find_filesystem_name_by_bucket_arn(client, bucket_arn)
    assert fs_name, f"Failed to find filesystem after onboarding {bucket_arn}"

    yield fs_name

    _remove_s3_filesystem(client, bucket_arn)


@pytest.fixture
def s3_rw_filesystem(
    res_environment: ResEnvironment,
    environment_name: str,
    region: str,
    admin: ClientAuth,
    request: pytest.FixtureRequest,
) -> Generator[str, None, None]:
    """Onboard a read-write S3 bucket; yield its filesystem name."""
    yield from _s3_filesystem_fixture(
        res_environment,
        environment_name,
        region,
        admin,
        request.config.getoption("--api-invoker-type"),
        S3_RW_STORAGE_NAME,
        S3_RW_MOUNT_DIR,
        read_only=False,
    )


@pytest.fixture
def s3_ro_filesystem(
    res_environment: ResEnvironment,
    environment_name: str,
    region: str,
    admin: ClientAuth,
    request: pytest.FixtureRequest,
) -> Generator[str, None, None]:
    """Onboard a read-only S3 bucket; yield its filesystem name."""
    yield from _s3_filesystem_fixture(
        res_environment,
        environment_name,
        region,
        admin,
        request.config.getoption("--api-invoker-type"),
        S3_RO_STORAGE_NAME,
        S3_RO_MOUNT_DIR,
        read_only=True,
    )


@pytest.fixture
def s3_persist_filesystem(
    res_environment: ResEnvironment,
    environment_name: str,
    region: str,
    admin: ClientAuth,
    request: pytest.FixtureRequest,
) -> Generator[str, None, None]:
    """Onboard a read-only S3 bucket for persistence testing."""
    yield from _s3_filesystem_fixture(
        res_environment,
        environment_name,
        region,
        admin,
        request.config.getoption("--api-invoker-type"),
        S3_PERSIST_STORAGE_NAME,
        S3_PERSIST_MOUNT_DIR,
        read_only=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.nightly
@pytest.mark.requires_vdi
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestS3Mount:
    """
    S3 mount point validation.

    S3 buckets are onboarded via fixtures before the project is created.
    The project fixture resolves "fixture:s3_*_filesystem" entries in
    filesystem_names, attaching the S3 filesystem to the project so the
    VDI bootstrap mounts it at first boot.
    """

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-s3-mount" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-s3-mount" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES S3 mount integration test project",
                    enable_budgets=False,
                ),
                ["home", "fixture:s3_rw_filesystem", "fixture:s3_ro_filesystem"],
                ["RESAdministrators", "group_1", "group_2"],
                [],
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [(AL2023_SOFTWARE_STACK, "project", "admin")],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="s3mnt",
                    description="RES S3 mount test session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_s3_mount_present_and_functional(
        self,
        res_environment: ResEnvironment,
        environment_name: str,
        region: str,
        admin: ClientAuth,
        admin_username: str,
        s3_rw_filesystem: str,
        s3_ro_filesystem: str,
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        Verify that S3 mounts are present on the VDI and functional:
        - Read-write mount: write and read back a file.
        - Read-only mount: read a pre-seeded file, reject writes.
        """
        if not session:
            pytest.fail("Session fixture returned None — VDI launch failed")

        assert (
            session.state == VirtualDesktopSessionState.READY
        ), f"VDI did not reach READY: {session.state} ({session.failure_reason})"

        instance_id = session.server.instance_id
        bucket_name_rw = _get_test_bucket_name(
            environment_name, region, S3_RW_STORAGE_NAME
        )
        bucket_name_ro = _get_test_bucket_name(
            environment_name, region, S3_RO_STORAGE_NAME
        )
        test_prefix = f"{_TEST_MARKER}/{uuid.uuid4().hex[:8]}"

        # Seed a read-only test object directly in S3
        s3_client = boto3.client("s3", region_name=region)
        seed_key = f"{test_prefix}/seed.txt"
        seed_content = f"ro-seed-{uuid.uuid4()}"
        s3_client.put_object(
            Bucket=bucket_name_ro, Key=seed_key, Body=seed_content.encode()
        )

        try:
            # --- Verify RW mount ---
            mount_output = run_command(instance_id, "mount")
            if not command_succeeded(mount_output):
                pytest.fail(f"mount command failed. Output: {mount_output}")
            assert (
                S3_RW_MOUNT_DIR in mount_output
            ), f"RW mount dir {S3_RW_MOUNT_DIR} not in output: {mount_output}"

            # Write and read back
            test_content = f"{_TEST_MARKER}-{uuid.uuid4()}"
            test_file = f"{S3_RW_MOUNT_DIR}/{test_prefix}/verify.txt"
            write_output = run_command(
                instance_id,
                f"mkdir -p {S3_RW_MOUNT_DIR}/{test_prefix} && "
                f"echo {shlex.quote(test_content)} > {test_file}",
            )
            assert command_succeeded(
                write_output
            ), f"RW write failed. Output: {write_output}"
            read_output = run_command(instance_id, f"cat {test_file}")
            assert command_succeeded(
                read_output
            ), f"RW read failed. Output: {read_output}"
            assert (
                test_content in read_output
            ), f"Content mismatch. Expected '{test_content}' in: {read_output}"

            # --- Verify RO mount ---
            assert (
                S3_RO_MOUNT_DIR in mount_output
            ), f"RO mount dir {S3_RO_MOUNT_DIR} not in output: {mount_output}"

            # Read seeded file
            read_output = run_command(instance_id, f"cat {S3_RO_MOUNT_DIR}/{seed_key}")
            assert command_succeeded(
                read_output
            ), f"RO read failed. Output: {read_output}"
            assert (
                seed_content in read_output
            ), f"RO content mismatch. Expected '{seed_content}' in: {read_output}"

            # Write should fail (write to mount root to avoid ENOENT false positive)
            write_output = run_command(
                instance_id,
                f"echo 'fail' > {S3_RO_MOUNT_DIR}/blocked.txt",
            )
            assert not command_succeeded(
                write_output
            ), f"RO write should have been rejected. Output: {write_output}"

        finally:
            _cleanup_test_objects(bucket_name_rw, region, test_prefix)
            _cleanup_test_objects(bucket_name_ro, region, test_prefix)

    @pytest.mark.usefixtures("admin")
    @pytest.mark.parametrize("admin_username", ["admin1"])
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-s3-persist" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-s3-persist" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES S3 mount persistence test project",
                    enable_budgets=False,
                ),
                ["home", "fixture:s3_persist_filesystem"],
                ["RESAdministrators", "group_1", "group_2"],
                [],
                "admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [(AL2023_SOFTWARE_STACK, "project", "admin")],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="s3per",
                    description="RES S3 mount persistence test session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "admin",
            )
        ],
        indirect=True,
    )
    def test_s3_mount_persists_across_stop_start(
        self,
        res_environment: ResEnvironment,
        environment_name: str,
        region: str,
        admin: ClientAuth,
        admin_username: str,
        s3_persist_filesystem: str,
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        Verify that the S3 mount persists across a VDI stop/start cycle.
        """
        if not session:
            pytest.fail("Session fixture returned None — VDI launch failed")

        assert (
            session.state == VirtualDesktopSessionState.READY
        ), f"VDI did not reach READY: {session.state} ({session.failure_reason})"

        instance_id = session.server.instance_id

        # Verify mount after initial launch
        mount_output = run_command(instance_id, "mount")
        if not command_succeeded(mount_output):
            pytest.fail(f"mount command failed after launch. Output: {mount_output}")
        assert (
            S3_PERSIST_MOUNT_DIR in mount_output
        ), f"Mount dir {S3_PERSIST_MOUNT_DIR} not found. Output: {mount_output}"

        # Stop/start and verify persistence
        api_client = ApiClient(res_environment, admin)
        logger.info("Stopping/starting VDI for persistence check...")
        session = _stop_and_start_vdi(api_client, session)
        instance_id = session.server.instance_id

        mount_output = run_command(instance_id, "mount")
        assert command_succeeded(
            mount_output
        ), f"mount command failed after stop/start. Output: {mount_output}"
        assert S3_PERSIST_MOUNT_DIR in mount_output, (
            f"Mount dir {S3_PERSIST_MOUNT_DIR} not found after stop/start. "
            f"Output: {mount_output}"
        )
