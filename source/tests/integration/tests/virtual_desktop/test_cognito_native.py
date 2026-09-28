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

import logging
import os
import uuid
from typing import Any, Optional

import pytest
from res.constants import (  # type: ignore
    COGNITO_USER_IDP_TYPE,
    PROJECT_MEMBER_ROLE_ID,
    PROJECT_ROLE_ASSIGNMENT_TYPE,
    ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
    USER_ROLE,
)

# Role-assignment/user request types and Project still go through the not-yet-migrated
# cluster-manager API, so they stay ideadatamodel.
from ideadatamodel import (  # type: ignore
    BatchDeleteRoleAssignmentRequest,
    BatchPutRoleAssignmentRequest,
    DeleteRoleAssignmentRequest,
    GetUserRequest,
    Project,
    PutRoleAssignmentRequest,
)
from tests.integration.framework.client.api_client import (
    ApiClient,
    BatchCreateSessionRequestContent,
)
from tests.integration.framework.client.res_client import ResClient
from tests.integration.framework.fixtures.project import project
from tests.integration.framework.fixtures.res_environment import (
    ResEnvironment,
    res_environment,
)
from tests.integration.framework.fixtures.session import session
from tests.integration.framework.fixtures.software_stack import software_stack
from tests.integration.framework.fixtures.users.cognito_admin import cognito_admin
from tests.integration.framework.fixtures.users.cognito_non_admin import (
    cognito_non_admin,
)
from tests.integration.framework.model.client_auth import ClientAuth
from tests.integration.framework.utils.model_utils import get_backend_model_class
from tests.integration.framework.utils.vdi_command_utils import (
    command_succeeded,
    run_command,
    run_command_as,
)
from tests.integration.tests.smoke.config import (
    AL2023_SOFTWARE_STACK,
    TEST_SOFTWARE_STACKS,
)

# Backend data-model classes (source/idea/data-model). The session APIs consume
# and return these.
VirtualDesktopSession = get_backend_model_class(
    "virtual_desktop_session", "VirtualDesktopSession"
)
VirtualDesktopSoftwareStack = get_backend_model_class(
    "virtual_desktop_software_stack", "VirtualDesktopSoftwareStack"
)
VirtualDesktopBaseOS = get_backend_model_class(
    "virtual_desktop_base_os", "VirtualDesktopBaseOs"
)

# First Windows stack in the shared smoke config (selected by base_os rather than
# a fixed index so it survives reordering of TEST_SOFTWARE_STACKS).
WINDOWS_SOFTWARE_STACK = next(
    stack
    for stack in TEST_SOFTWARE_STACKS
    if stack.base_os == VirtualDesktopBaseOS.WINDOWS
)

logger = logging.getLogger(__name__)

COGNITO_AUTH_CACHE = "/opt/cognito_auth/cache.json"


@pytest.fixture
def cognito_non_admin_member(
    request: pytest.FixtureRequest,
    res_environment: ResEnvironment,
    cognito_admin: ClientAuth,
    cognito_non_admin: ClientAuth,
    project: Project,
) -> ClientAuth:
    """
    Grant the non-admin cognito user membership of the parametrized project and
    return its auth. Used as the session owner so the VDI launches for a
    non-admin (its username is generated at fixture time, so it can't be listed
    statically in the project fixture's users).
    """
    api_invoker_type = request.config.getoption("--api-invoker-type")
    admin_client = ResClient(res_environment, cognito_admin, api_invoker_type)
    admin_client.batch_put_role_assignment(
        BatchPutRoleAssignmentRequest(
            items=[
                PutRoleAssignmentRequest(
                    resource_id=project.project_id,
                    resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                    actor_id=cognito_non_admin.username,
                    actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                    role_id=PROJECT_MEMBER_ROLE_ID,
                    request_id="test",
                )
            ]
        )
    )
    request.addfinalizer(
        lambda: admin_client.batch_delete_role_assignment(
            BatchDeleteRoleAssignmentRequest(
                items=[
                    DeleteRoleAssignmentRequest(
                        resource_id=project.project_id,
                        resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                        actor_id=cognito_non_admin.username,
                        actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                        request_id="test",
                    )
                ]
            )
        )
    )
    return cognito_non_admin


@pytest.mark.nightly
@pytest.mark.requires_vdi
@pytest.mark.in_vdi
@pytest.mark.linux_only
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestCognitoNative:
    """
    Cognito-native user checks (doc: "Cognito native user based Authentication"
    + "VDI Security"). A single Linux VDI is launched for the cognito user
    (clusteradmin) and the in-guest state is asserted over SSM.
    """

    @pytest.mark.usefixtures("cognito_admin")
    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-cognito-native"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-cognito-native"
                    + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES cognito-native in-VDI test project",
                    enable_budgets=False,
                ),
                ["home"],
                # Cognito users are added as project members via the users list
                # (not AD groups), so create-session recognizes their membership.
                [],
                ["clusteradmin"],
                "cognito_admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [(AL2023_SOFTWARE_STACK, "project", "cognito_admin")],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="cog",
                    description="RES cognito-native in-VDI test session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "cognito_admin",
            )
        ],
        indirect=True,
    )
    def test_cognito_native_in_vdi(
        self,
        cognito_admin: ClientAuth,
        # project and software_stack are not read directly, but must be declared
        # so their indirect parametrization binds — the session fixture resolves
        # them at runtime via getfixturevalue.
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        Walk a single cognito-user Linux VDI through the in-guest checks:
        1. Home directory exists and is owned by the cognito user.
        2. ~/.ssh exists with an RSA key (PAM ssh_keygen creates it on first login).
        3. A file can be written to and read back from the attached (home) filesystem.
        4. The cognito admin has sudo access.
        5. root can read /opt/cognito_auth/cache.json.
        """
        # Fail loud rather than skip: a skipped test still goes green in
        # CodeBuild, hiding a VDI that never launched.
        assert session, "VDI session was not created"

        instance_id = session.server.instance_id
        user = session.owner

        # 1. Home directory exists and is owned by the cognito user.
        home = f"/home/{user}"
        output = run_command(instance_id, f"stat -c '%U' {home}")
        assert user in output, f"{home} not owned by {user}: {output}"

        # 2. ~/.ssh exists with an RSA private key.
        output = run_command(instance_id, f"test -f {home}/.ssh/id_rsa")
        assert command_succeeded(output), f"{home}/.ssh/id_rsa not found: {output}"

        # 3. Write then read a file on the attached (home) filesystem.
        marker = f"cognito-fs-{uuid.uuid4().hex[:8]}"
        test_file = f"{home}/{marker}.txt"
        output = run_command(
            instance_id,
            f"echo {marker} > {test_file} && cat {test_file} && rm -f {test_file}",
        )
        assert marker in output, f"fs write/read failed: {output}"

        # 4. Cognito admin has sudo rights. RES grants sudo with a password (no
        # NOPASSWD), so `sudo -n` can't be used; query the entitlement as root
        # instead — `sudo -l -U <user>` lists what the user may run.
        output = run_command(instance_id, f"sudo -l -U {user} | grep -q '(ALL' ")
        assert command_succeeded(output), f"cognito admin lacks sudo: {output}"

        # 5. root can read the cognito auth cache.
        output = run_command(instance_id, f"cat {COGNITO_AUTH_CACHE}")
        assert command_succeeded(
            output
        ), f"root could not read {COGNITO_AUTH_CACHE}: {output}"

    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-cognito-na" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-cognito-na" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES cognito non-admin in-VDI test project",
                    enable_budgets=False,
                ),
                ["home"],
                [],
                ["clusteradmin"],
                "cognito_admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [(AL2023_SOFTWARE_STACK, "project", "cognito_admin")],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "session",
        [
            (
                VirtualDesktopSession(
                    name="cog-na",
                    description="RES cognito non-admin in-VDI test session",
                    hibernation_enabled=False,
                ),
                "project",
                "software_stack",
                "cognito_non_admin_member",
            )
        ],
        indirect=True,
    )
    def test_cognito_non_admin_denied_auth_cache(
        self,
        cognito_non_admin_member: ClientAuth,
        project: Project,
        software_stack: Any,
        session: Optional[Any],
    ) -> None:
        """
        A non-admin cognito user must not be able to read the cognito auth cache
        (doc "VDI Security"). The VDI is owned by the non-admin user, so the check
        runs as that user; without sudo the read is denied.
        """
        # Fail loud rather than skip: a skipped test still goes green in
        # CodeBuild, hiding a VDI that never launched.
        assert session, "VDI session was not created"

        instance_id = session.server.instance_id
        user = session.owner

        # Run as the non-admin owner (SSM itself runs as root). Without sudo, both
        # a direct read and a sudo attempt must be denied.
        output = run_command_as(instance_id, user, f"cat {COGNITO_AUTH_CACHE}")
        assert not command_succeeded(
            output
        ), f"non-admin unexpectedly read {COGNITO_AUTH_CACHE}: {output}"

        output = run_command_as(instance_id, user, f"sudo -n cat {COGNITO_AUTH_CACHE}")
        assert not command_succeeded(
            output
        ), f"non-admin unexpectedly read {COGNITO_AUTH_CACHE} via sudo: {output}"


@pytest.mark.dev
@pytest.mark.usefixtures("res_environment")
@pytest.mark.usefixtures("region")
class TestCognitoNativeApi:
    """Cognito-native API-level checks that do not need a launched VDI."""

    @pytest.mark.parametrize(
        "project",
        [
            (
                Project(
                    title="res-cognito-win" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    name="res-cognito-win" + os.environ.get("PYTEST_XDIST_WORKER", ""),
                    description="RES cognito windows-block test project",
                    enable_budgets=False,
                ),
                ["home"],
                # The project is created by clusteradmin; the non-admin cognito
                # user is added as a member in the test (its username is generated
                # at fixture time, so it can't be named in this static list).
                [],
                ["clusteradmin"],
                "cognito_admin",
            )
        ],
        indirect=True,
    )
    @pytest.mark.parametrize(
        "software_stack",
        [(WINDOWS_SOFTWARE_STACK, "project", "cognito_admin")],
        indirect=True,
    )
    def test_cognito_user_cannot_create_windows_session(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        cognito_admin: ClientAuth,
        cognito_non_admin: ClientAuth,
        project: Project,
        software_stack: Any,
    ) -> None:
        """
        A non-admin cognito (native) user cannot create a non-Linux (Windows)
        session; the backend rejects it with a 400 before any VDI is launched.

        Admins bypass this check, so the test uses a non-admin cognito user. The
        Windows stack is created and enabled for the project by the software_stack
        fixture, and the user is granted project membership below, so the request
        reaches the OS check rather than being rejected earlier for an unknown
        stack or missing create-session permission.
        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        admin_client = ResClient(res_environment, cognito_admin, api_invoker_type)
        admin_client.batch_put_role_assignment(
            BatchPutRoleAssignmentRequest(
                items=[
                    PutRoleAssignmentRequest(
                        resource_id=project.project_id,
                        resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                        actor_id=cognito_non_admin.username,
                        actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                        role_id=PROJECT_MEMBER_ROLE_ID,
                        request_id="test",
                    )
                ]
            )
        )
        request.addfinalizer(
            lambda: admin_client.batch_delete_role_assignment(
                BatchDeleteRoleAssignmentRequest(
                    items=[
                        DeleteRoleAssignmentRequest(
                            resource_id=project.project_id,
                            resource_type=PROJECT_ROLE_ASSIGNMENT_TYPE,
                            actor_id=cognito_non_admin.username,
                            actor_type=ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
                            request_id="test",
                        )
                    ]
                )
            )
        )

        api_client = ApiClient(res_environment, cognito_non_admin)
        payload = {
            "sessions": [
                {
                    "name": "cog-win",
                    "hibernation_enabled": False,
                    "base_os": software_stack.base_os,
                    "software_stack_id": software_stack.stack_id,
                    "server": {
                        "instance_type": "t3.2xlarge",
                        "root_volume_size": {"value": 50, "unit": "gb"},
                    },
                    "project": {"project_id": project.project_id},
                }
            ]
        }

        response = api_client.batch_create_session(
            BatchCreateSessionRequestContent(**payload)
        )
        assert (
            response.unsuccessful_list and len(response.unsuccessful_list) > 0  # type: ignore[attr-defined]
        ), "Expected the session to be rejected, but it was created successfully"
        failure = response.unsuccessful_list[0]  # type: ignore[attr-defined]
        assert (
            "not allowed to create non-Linux sessions" in failure.message
        ), f"Unexpected error message: {failure.message}"

    def test_cognito_non_admin_synced_as_native_user(
        self,
        request: pytest.FixtureRequest,
        res_environment: ResEnvironment,
        cognito_admin: ClientAuth,
        cognito_non_admin: ClientAuth,
    ) -> None:
        """
        A newly created native pool user is synced into RES as a non-admin native
        user with a uid (the create-session identity check requires one).
        """
        api_invoker_type = request.config.getoption("--api-invoker-type")
        client = ResClient(res_environment, cognito_admin, api_invoker_type)
        user = client.get_user(GetUserRequest(username=cognito_non_admin.username)).user

        assert user.identity_source == COGNITO_USER_IDP_TYPE, user.identity_source
        assert user.role == USER_ROLE, user.role
        assert not user.sudo, "non-admin cognito user should not have sudo"
        assert user.uid, "synced cognito user is missing a uid"
