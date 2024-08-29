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
Test Cases for ProjectsService
"""

from typing import List, Optional
from unittest.mock import MagicMock

import botocore.exceptions
import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideaclustermanager import AppContext
from ideasdk.aws import AwsClientProvider
from ideasdk.utils import Utils

from ideadatamodel import (
    CreateProjectRequest,
    DeleteProjectRequest,
    DeleteRoleAssignmentRequest,
    DisableProjectRequest,
    EnableProjectRequest,
    GetProjectRequest,
    GetUserProjectsRequest,
    Group,
    ListProjectsRequest,
    Project,
    PutRoleAssignmentRequest,
    SocaAnyPayload,
    SocaKeyValue,
    UpdateProjectRequest,
    User,
    VirtualDesktopSession,
    VirtualDesktopSoftwareStack,
    constants,
    errorcodes,
    exceptions,
)


class ProjectsTestContext:
    crud_project: Optional[Project]


def generate_random_id(prefix: str) -> str:
    return f"test-{prefix}-{Utils.short_uuid()}"


def enable_project(context: AppContext, project: Project):
    context.projects.enable_project(EnableProjectRequest(project_id=project.project_id))


def disable_project(context: AppContext, project: Project):
    context.projects.disable_project(
        DisableProjectRequest(project_id=project.project_id)
    )


def is_assigned(context: AppContext, user: User, project: Project) -> bool:
    result = context.projects.get_user_projects(
        GetUserProjectsRequest(username=user.username)
    )
    for member_project in result.projects:
        if project.project_id == member_project.project_id:
            return True
    return False


def create_role_assignment(
    context: AppContext,
    actor_id: str,
    actor_type: str,
    resource_id: str,
    resource_type: str,
    role_id: str,
):
    response = context.role_assignments.put_role_assignment(
        PutRoleAssignmentRequest(
            request_id=generate_random_id("req"),
            actor_id=actor_id,
            resource_id=resource_id,
            resource_type=resource_type,
            actor_type=actor_type,
            role_id=role_id,
        )
    )
    assert response is not None


def delete_role_assignment(
    context: AppContext,
    actor_id: str,
    actor_type: str,
    resource_id: str,
    resource_type: str,
):
    response = context.role_assignments.delete_role_assignment(
        DeleteRoleAssignmentRequest(
            request_id=generate_random_id("req"),
            actor_id=actor_id,
            resource_id=resource_id,
            actor_type=actor_type,
            resource_type=resource_type,
        )
    )
    assert response is not None


def clear_assignments(context: AppContext, membership, actor_id: str, actor_type: str):
    projects = [membership.project_a, membership.project_b]
    for project in projects:
        delete_role_assignment(
            context, actor_id, actor_type, project.project_id, "project"
        )


def create_mock_project(context: AppContext):
    name = generate_random_id("sampleproject")
    create_project_request = CreateProjectRequest(
        project=Project(
            name=name,
            title="Sample Project",
            description="Sample Project Description",
            tags=[
                SocaKeyValue(key="k1", value="v1"),
                SocaKeyValue(key="k2", value="v2"),
            ],
        )
    )

    project_id = context.projects.create_project(
        create_project_request
    ).project.project_id
    return {"project_id": project_id, "name": name}


@pytest.fixture(scope="module")
def monkey_session(request):
    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="module")
def membership(context: AppContext, monkey_session):
    monkey_session.setattr(
        context.accounts.sssd, "get_uid_and_gid_for_user", lambda x: (1000, 1000)
    )
    monkey_session.setattr(context.accounts.sssd, "get_gid_for_group", lambda x: 1000)
    monkey_session.setattr(
        context.role_assignments,
        "verify_actor_exists",
        lambda actor_id, actor_type: True,
    )
    monkey_session.setattr(
        context.role_assignments,
        "verify_resource_exists",
        lambda resource_id, resource_type: True,
    )

    def create_group(group_name: str) -> Group:
        group = context.accounts.create_group(
            Group(
                title=f"{group_name} Project Group",
                name=f"{group_name}-project-group"[
                    : constants.AD_SAM_ACCOUNT_NAME_MAX_LENGTH
                ],
                group_type=constants.GROUP_TYPE_PROJECT,
            )
        )
        assert group is not None
        return group

    def create_project(project_name: str, project_title: str) -> Project:
        # create project
        result = context.projects.create_project(
            CreateProjectRequest(
                project=Project(
                    name=project_name,
                    title=project_title,
                )
            )
        )
        assert result is not None
        assert result.project is not None

        # enable project
        enable_project(context=context, project=result.project)

        # get enabled project
        result = context.projects.get_project(
            GetProjectRequest(project_id=result.project.project_id)
        )

        assert result.project is not None
        assert result.project.enabled is True
        ProjectsTestContext.project = result.project

        return result.project

    def create_user(
        username: str, gid: int, uid: int, additional_groups: List[str]
    ) -> User:
        return context.accounts.create_user(
            user=User(
                username=username,
                password="MockPassword_123",
                email=f"{username}@example.com",
                uid=uid,
                gid=gid,
                home_dir=f"/home/{username}",
                login_shell="/bin/bash",
                additional_groups=additional_groups,
            ),
            email_verified=True,
        )

    group_a1 = create_group("group_a1")
    group_a2 = create_group("group_a2")
    group_b = create_group("group_b")
    default_group = create_group("default_group")
    project_a = create_project("project-a", "Project A")
    project_b = create_project("project-b", "Project B")
    user_1 = create_user(
        username="project_user_1",
        uid=1000,
        gid=1000,
        additional_groups=[default_group.name],
    )
    user_2 = create_user(
        username="project_user_2",
        uid=1001,
        gid=1001,
        additional_groups=[default_group.name],
    )
    user_3 = create_user(
        username="project_user_3",
        uid=1002,
        gid=1002,
        additional_groups=[default_group.name],
    )

    context.accounts.activate_user(user_1)
    context.accounts.activate_user(user_2)
    context.accounts.activate_user(user_3)

    return SocaAnyPayload(
        group_a1=group_a1,
        group_a2=group_a2,
        group_b=group_b,
        project_a=project_a,
        project_b=project_b,
        user_1=user_1,
        user_2=user_2,
        user_3=user_3,
    )


def test_projects_crud_create_project(context):
    """
    create project
    """
    name = generate_random_id("sampleproject")
    result = context.projects.create_project(
        CreateProjectRequest(
            project=Project(
                name=name,
                title="Sample Project",
                description="Sample Project Description",
                tags=[
                    SocaKeyValue(key="k1", value="v1"),
                    SocaKeyValue(key="k2", value="v2"),
                ],
                scripts={
                    "linux": {
                        "on_vdi_start": [
                            {
                                "script_location": "file://example/bath",
                                "arguments": ["ex1", "ex2"],
                            }
                        ]
                    },
                    "windows": {
                        "on_vdi_configured": [
                            {
                                "script_location": "https://s3.amazonaws.com/bucket/example_file",
                                "arguments": ["ex1", "ex2"],
                            }
                        ]
                    },
                },
            )
        )
    )
    assert result is not None
    assert result.project is not None
    assert result.project.name == name
    ProjectsTestContext.crud_project = result.project

    result = context.projects.get_project(
        GetProjectRequest(project_name=ProjectsTestContext.crud_project.name)
    )
    assert result is not None
    assert result.project is not None
    assert result.project.enabled is True
    assert result.project.description is not None
    assert result.project.description == "Sample Project Description"
    assert result.project.tags is not None
    assert len(result.project.tags) == 2
    assert result.project.tags[0].key == "k1"
    assert result.project.tags[0].value == "v1"
    assert result.project.tags[1].key == "k2"
    assert result.project.tags[1].value == "v2"
    assert result.project.created_on is not None
    assert result.project.updated_on is not None


def test_projects_crud_create_project_invalid_script_location_fails(context):
    """
    create project
    """

    def _create_project_invalid_script_location_fails(os: str):
        name = generate_random_id("sampleproject")
        request = CreateProjectRequest(
            project=Project(
                name=name,
                title="Sample Project",
                description="Sample Project Description",
                tags=[
                    SocaKeyValue(key="k1", value="v1"),
                    SocaKeyValue(key="k2", value="v2"),
                ],
                scripts={
                    os: {
                        "on_vdi_start": [
                            {
                                "script_location": "invalid_script_location",
                                "arguments": ["ex1", "ex2"],
                            }
                        ]
                    }
                },
            )
        )
        with pytest.raises(exceptions.SocaException) as exc_info:
            context.projects.create_project(request)
        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert constants.SCRIPT_LOCATION_ERROR_MESSAGE in exc_info.value.message

    _create_project_invalid_script_location_fails("windows")
    _create_project_invalid_script_location_fails("linux")


def test_projects_crud_create_project_invalid_security_group_fails(
    context, monkey_session
):
    """
    create project
    """

    mock_ec2 = SocaAnyPayload()
    mock_ec2.describe_security_groups = MagicMock(return_value={"SecurityGroups": []})
    monkey_session.setattr(AwsClientProvider, "ec2", lambda *_: mock_ec2)

    invalid_security_group_id = "invalid_security_group"
    name = generate_random_id("sampleproject")

    request = CreateProjectRequest(
        project=Project(
            name=name,
            title="Sample Project",
            description="Sample Project Description",
            tags=[
                SocaKeyValue(key="k1", value="v1"),
                SocaKeyValue(key="k2", value="v2"),
            ],
            security_groups=[invalid_security_group_id],
        )
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.projects.create_project(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.SECURITY_GROUP_ERROR_MESSAGE in exc_info.value.message


def test_projects_crud_create_project_valid_security_group_succeeds(
    context, monkey_session
):
    """
    create project
    """
    valid_security_group_id = "valid_security_group"

    mock_ec2 = SocaAnyPayload()
    mock_ec2.describe_security_groups = MagicMock(
        return_value={"SecurityGroups": [{"GroupId": valid_security_group_id}]}
    )
    monkey_session.setattr(AwsClientProvider, "ec2", lambda *_: mock_ec2)

    name = generate_random_id("sampleproject")

    request = CreateProjectRequest(
        project=Project(
            name=name,
            title="Sample Project",
            description="Sample Project Description",
            tags=[
                SocaKeyValue(key="k1", value="v1"),
                SocaKeyValue(key="k2", value="v2"),
            ],
            security_groups=[valid_security_group_id],
        )
    )

    result = context.projects.create_project(request)
    assert result is not None
    assert result.project is not None
    assert result.project.name == name
    ProjectsTestContext.crud_project = result.project

    result = context.projects.get_project(
        GetProjectRequest(project_name=ProjectsTestContext.crud_project.name)
    )
    assert result is not None
    assert result.project is not None
    assert result.project.enabled is True
    assert result.project.description is not None
    assert result.project.description == "Sample Project Description"
    assert result.project.tags is not None
    assert len(result.project.tags) == 2
    assert result.project.tags[0].key == "k1"
    assert result.project.tags[0].value == "v1"
    assert result.project.tags[1].key == "k2"
    assert result.project.tags[1].value == "v2"
    assert result.project.created_on is not None
    assert result.project.updated_on is not None
    assert result.project.security_groups[0] == valid_security_group_id


def test_projects_crud_create_project_invalid_policy_arn_fails(context, monkey_session):
    """
    create project
    """

    mock_iam = SocaAnyPayload()
    mock_iam.get_policy = MagicMock()
    mock_iam.get_policy.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "MockedErrorCode", "Message": "MockedErrorMessage"}},
        "operation_name",
    )
    monkey_session.setattr(AwsClientProvider, "iam", lambda *_: mock_iam)

    invalid_policy_arn = "invalid_policy_arn"
    name = generate_random_id("sampleproject")

    request = CreateProjectRequest(
        project=Project(
            name=name,
            title="Sample Project",
            description="Sample Project Description",
            tags=[
                SocaKeyValue(key="k1", value="v1"),
                SocaKeyValue(key="k2", value="v2"),
            ],
            policy_arns=[invalid_policy_arn],
        )
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.projects.create_project(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.POLICY_ARN_ERROR_MESSAGE in exc_info.value.message


def test_projects_crud_create_project_valid_policy_arn_create_new_role_succeeds(
    context, monkey_session
):
    """
    create project
    """

    mock_iam = SocaAnyPayload()
    mock_iam.get_policy = MagicMock()
    mock_iam.create_instance_profile = MagicMock()
    mock_iam.create_role = MagicMock()
    mock_iam.attach_role_policy = MagicMock()
    mock_iam.add_role_to_instance_profile = MagicMock()
    monkey_session.setattr(AwsClientProvider, "iam", lambda *_: mock_iam)
    name = generate_random_id("sampleproject")

    request = CreateProjectRequest(
        project=Project(
            name=name,
            title="Sample Project",
            description="Sample Project Description",
            tags=[
                SocaKeyValue(key="k1", value="v1"),
                SocaKeyValue(key="k2", value="v2"),
            ],
            policy_arns=["valid_policy_arn"],
        )
    )
    result = context.projects.create_project(request)
    assert result is not None
    assert result.project is not None
    assert result.project.name == name
    ProjectsTestContext.crud_project = result.project

    result = context.projects.get_project(
        GetProjectRequest(project_name=ProjectsTestContext.crud_project.name)
    )
    assert result is not None
    assert result.project is not None
    assert result.project.enabled is True
    assert result.project.description is not None
    assert result.project.description == "Sample Project Description"
    assert result.project.tags is not None
    assert len(result.project.tags) == 2
    assert result.project.tags[0].key == "k1"
    assert result.project.tags[0].value == "v1"
    assert result.project.tags[1].key == "k2"
    assert result.project.tags[1].value == "v2"
    assert result.project.created_on is not None
    assert result.project.updated_on is not None
    assert result.project.policy_arns[0] == "valid_policy_arn"


def test_projects_crud_create_project_valid_policy_arn_create_new_role_fails_should_roll_back(
    context, monkey_session
):
    """
    create project
    """

    mock_iam = SocaAnyPayload()
    mock_iam.get_policy = MagicMock()
    mock_iam.create_instance_profile = MagicMock()
    mock_iam.create_role = MagicMock()
    mock_iam.attach_role_policy = MagicMock()
    mock_iam.add_role_to_instance_profile = MagicMock()
    mock_iam.add_role_to_instance_profile.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "MockedErrorCode", "Message": "MockedErrorMessage"}},
        "operation_name",
    )

    mock_iam.detach_role_policy = MagicMock()
    mock_iam.delete_role = MagicMock()
    mock_iam.delete_instance_profile = MagicMock()

    monkey_session.setattr(AwsClientProvider, "iam", lambda *_: mock_iam)
    name = generate_random_id("sampleproject")

    request = CreateProjectRequest(
        project=Project(
            name=name,
            title="Sample Project",
            description="Sample Project Description",
            tags=[
                SocaKeyValue(key="k1", value="v1"),
                SocaKeyValue(key="k2", value="v2"),
            ],
            policy_arns=["valid_policy_arn"],
        )
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.projects.create_project(request)
    assert exc_info.value.error_code == errorcodes.GENERAL_ERROR
    assert "Could not create role with given policies" in exc_info.value.message
    mock_iam.detach_role_policy.assert_called()
    mock_iam.delete_role.assert_called()
    mock_iam.delete_instance_profile.assert_called()


def test_projects_crud_update_project_invalid_script_location_fails(
    context, monkey_session
):
    """
    update project
    """

    mock_project = create_mock_project(context)
    project_id = mock_project["project_id"]

    def _update_project_invalid_script_location_fails(os: str):
        request = UpdateProjectRequest(
            project=Project(
                project_id=project_id,
                scripts={
                    os: {
                        "on_vdi_start": [
                            {
                                "script_location": "invalid_script_location",
                                "arguments": ["ex1", "ex2"],
                            }
                        ]
                    }
                },
            )
        )
        with pytest.raises(exceptions.SocaException) as exc_info:
            context.projects.update_project(request)
        assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
        assert constants.SCRIPT_LOCATION_ERROR_MESSAGE in exc_info.value.message

    _update_project_invalid_script_location_fails("windows")
    _update_project_invalid_script_location_fails("linux")


def test_projects_crud_update_project_invalid_security_group_fails(
    context, monkey_session
):
    """
    update project
    """

    mock_project = create_mock_project(context)
    project_id = mock_project["project_id"]

    mock_ec2 = SocaAnyPayload()
    mock_ec2.describe_security_groups = MagicMock(return_value={"SecurityGroups": []})
    monkey_session.setattr(AwsClientProvider, "ec2", lambda *_: mock_ec2)

    invalid_security_group_id = "invalid_security_group"

    request = UpdateProjectRequest(
        project=Project(
            project_id=project_id, security_groups=[invalid_security_group_id]
        )
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.projects.update_project(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.SECURITY_GROUP_ERROR_MESSAGE in exc_info.value.message


def test_projects_crud_update_project_invalid_policy_arn_fails(context, monkey_session):
    """
    update project
    """

    mock_project = create_mock_project(context)
    project_id = mock_project["project_id"]

    mock_iam = SocaAnyPayload()
    mock_iam.get_policy = MagicMock()
    mock_iam.get_policy.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "MockedErrorCode", "Message": "MockedErrorMessage"}},
        "operation_name",
    )
    monkey_session.setattr(AwsClientProvider, "iam", lambda *_: mock_iam)

    invalid_policy_arn = "invalid_policy_arn"

    request = UpdateProjectRequest(
        project=Project(project_id=project_id, policy_arns=[invalid_policy_arn])
    )

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.projects.update_project(request)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert constants.POLICY_ARN_ERROR_MESSAGE in exc_info.value.message


def test_projects_crud_update_project_with_new_policy_arns_succeeds(
    context, monkey_session
):
    """
    update project
    """

    mock_project = create_mock_project(context)
    project_id = mock_project["project_id"]
    name = mock_project["name"]

    mock_iam = SocaAnyPayload()
    mock_iam.get_policy = MagicMock()
    mock_iam.create_instance_profile = MagicMock()
    mock_iam.create_role = MagicMock()
    mock_iam.attach_role_policy = MagicMock()
    mock_iam.add_role_to_instance_profile = MagicMock()
    mock_iam.get_role = MagicMock()
    mock_iam.get_role.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "NoSuchEntityException", "Message": "MockedErrorMessage"}},
        "operation_name",
    )
    monkey_session.setattr(AwsClientProvider, "iam", lambda *_: mock_iam)

    request = UpdateProjectRequest(
        project=Project(project_id=project_id, policy_arns=["valid_policy_arn"])
    )

    result = context.projects.update_project(request)
    assert result is not None
    assert result.project is not None
    assert result.project.name == name
    # Ensure if role was never created, that it will create one
    mock_iam.create_role.assert_called()

    ProjectsTestContext.crud_project = result.project

    result = context.projects.get_project(
        GetProjectRequest(project_name=ProjectsTestContext.crud_project.name)
    )
    assert result is not None
    assert result.project is not None
    assert result.project.enabled is True
    assert result.project.description is not None
    assert result.project.description == "Sample Project Description"
    assert result.project.tags is not None
    assert len(result.project.tags) == 2
    assert result.project.tags[0].key == "k1"
    assert result.project.tags[0].value == "v1"
    assert result.project.tags[1].key == "k2"
    assert result.project.tags[1].value == "v2"
    assert result.project.created_on is not None
    assert result.project.updated_on is not None
    assert result.project.policy_arns[0] == "valid_policy_arn"


def test_projects_crud_create_project_url_error(context):
    """
    create project
    """
    group = context.accounts.create_group(
        Group(
            title=f"Sample Project Group URL",
            name=f"sample-project-group-url",
            group_type=constants.GROUP_TYPE_PROJECT,
        )
    )

    assert group is not None

    with pytest.raises(exceptions.SocaException) as exc_info:
        context.projects.create_project(
            CreateProjectRequest(
                project=Project(
                    name="sampleproject",
                    title="Sample Project",
                    description="Sample Project Description",
                    ldap_groups=["sample-project-group-url"],
                    tags=[
                        SocaKeyValue(key="k1", value="v1"),
                        SocaKeyValue(key="k2", value="v2"),
                    ],
                    scripts={
                        "linux": {
                            "on_vdi_start": [
                                {
                                    "script_location": "wrong_url",
                                    "arguments": ["ex1", "ex2"],
                                }
                            ]
                        }
                    },
                )
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS


def test_projects_crud_get_project_by_name(context):
    """
    get project by name
    """
    assert ProjectsTestContext.crud_project is not None

    result = context.projects.get_project(
        GetProjectRequest(project_name=ProjectsTestContext.crud_project.name)
    )
    assert result is not None
    assert result.project is not None
    assert result.project.name == ProjectsTestContext.crud_project.name
    assert result.project.project_id == ProjectsTestContext.crud_project.project_id


def test_projects_crud_get_project_by_id(context):
    """
    get project by id
    """
    assert ProjectsTestContext.crud_project is not None

    result = context.projects.get_project(
        GetProjectRequest(project_id=ProjectsTestContext.crud_project.project_id)
    )
    assert result is not None
    assert result.project is not None
    assert result.project.name == ProjectsTestContext.crud_project.name
    assert result.project.project_id == ProjectsTestContext.crud_project.project_id


def test_projects_crud_get_project_invalid_should_fail(context):
    """
    get project - invalid project id or name
    """

    # by project id
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.projects.get_project(GetProjectRequest(project_id="unknown-project-id"))
    assert exc_info.value.error_code == errorcodes.PROJECT_NOT_FOUND

    # by project name
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.projects.get_project(
            GetProjectRequest(project_name="unknown-project-name")
        )
    assert exc_info.value.error_code == errorcodes.PROJECT_NOT_FOUND


def test_projects_crud_enable_project(context):
    """
    enable project
    """
    assert ProjectsTestContext.crud_project is not None

    context.projects.enable_project(
        EnableProjectRequest(project_id=ProjectsTestContext.crud_project.project_id)
    )

    result = context.projects.get_project(
        GetProjectRequest(project_id=ProjectsTestContext.crud_project.project_id)
    )
    assert result is not None
    assert result.project is not None
    assert result.project.enabled is True


def test_projects_crud_disable_project(context):
    """
    disable project
    """
    assert ProjectsTestContext.crud_project is not None

    context.projects.disable_project(
        DisableProjectRequest(project_id=ProjectsTestContext.crud_project.project_id)
    )

    result = context.projects.get_project(
        GetProjectRequest(project_id=ProjectsTestContext.crud_project.project_id)
    )
    assert result is not None
    assert result.project is not None
    assert result.project.enabled is False


def test_projects_crud_list_projects(context):
    """
    list projects
    """
    assert ProjectsTestContext.crud_project is not None

    result = context.projects.list_projects(ListProjectsRequest())

    assert result is not None
    assert result.listing is not None
    assert len(result.listing) > 0

    found = None
    for project in result.listing:
        if project.project_id == ProjectsTestContext.crud_project.project_id:
            found = project
            break

    assert found is not None


def test_project_crud_update_project_tags(context):
    assert ProjectsTestContext.crud_project is not None

    result = context.projects.get_project(
        GetProjectRequest(project_id=ProjectsTestContext.crud_project.project_id)
    )

    project = result.project

    initial_number_of_tags = len(project.tags)

    project.tags.append(SocaKeyValue(key="test-key-u", value="test-value-u"))

    context.projects.update_project(UpdateProjectRequest(project=project))

    result = context.projects.get_project(
        GetProjectRequest(project_id=ProjectsTestContext.crud_project.project_id)
    )

    assert len(result.project.tags) is initial_number_of_tags + 1


def test_projects_crud_delete_project(context, membership):
    assert ProjectsTestContext.crud_project is not None
    create_role_assignment(
        context,
        membership.user_1.username,
        "user",
        ProjectsTestContext.crud_project.project_id,
        "project",
        "project_owner",
    )
    enable_project(context, ProjectsTestContext.crud_project)
    assert is_assigned(context, membership.user_1, ProjectsTestContext.crud_project)

    # First delete a project which are still used by sessions or software stacks
    context.projects.vdc_client.sessions = [VirtualDesktopSession()]
    context.projects.vdc_client.software_stacks = [VirtualDesktopSoftwareStack()]
    with pytest.raises(exceptions.SocaException) as excinfo:
        context.projects.delete_project(
            DeleteProjectRequest(project_id=ProjectsTestContext.crud_project.project_id)
        )
    assert excinfo.value.error_code == "GENERAL_ERROR"

    result = context.projects.get_project(
        GetProjectRequest(project_id=ProjectsTestContext.crud_project.project_id)
    )
    assert result.project is not None

    # Next delete a project which is not in use by any session or software stack
    context.projects.vdc_client.sessions = []
    context.projects.vdc_client.software_stacks = []
    context.projects.delete_project(
        DeleteProjectRequest(project_id=ProjectsTestContext.crud_project.project_id)
    )
    with pytest.raises(exceptions.SocaException) as excinfo:
        context.projects.get_project(
            GetProjectRequest(project_id=ProjectsTestContext.crud_project.project_id)
        )
    assert excinfo.value.error_code == "PROJECT_NOT_FOUND"


def test_projects_membership_setup(context, membership):
    """
    check if membership setup data is valid and tests are starting with a clean slate.
    """

    assert membership.project_a is not None
    assert membership.project_b is not None
    assert membership.user_1 is not None
    assert membership.user_2 is not None
    assert membership.user_3 is not None

    assert is_assigned(context, membership.user_1, membership.project_a) is False
    assert is_assigned(context, membership.user_2, membership.project_a) is False
    assert is_assigned(context, membership.user_3, membership.project_a) is False

    assert is_assigned(context, membership.user_1, membership.project_b) is False
    assert is_assigned(context, membership.user_2, membership.project_b) is False
    assert is_assigned(context, membership.user_3, membership.project_b) is False


def test_projects_assignment_added(context, membership):
    """
    assign user to project, unassign, and check if user is assigned to project
    """

    clear_assignments(context, membership, membership.user_1.username, "user")
    clear_assignments(context, membership, membership.user_2.username, "user")
    clear_assignments(context, membership, membership.user_3.username, "user")

    create_role_assignment(
        context,
        membership.user_1.username,
        "user",
        membership.project_a.project_id,
        "project",
        "project_owner",
    )
    assert is_assigned(context, membership.user_1, membership.project_a) is True

    create_role_assignment(
        context,
        membership.user_2.username,
        "user",
        membership.project_b.project_id,
        "project",
        "project_owner",
    )
    assert is_assigned(context, membership.user_2, membership.project_b) is True


def test_projects_assignment_removed(context, membership):
    """
    assign user to a project, unassign, and check if user is not assigned to project
    """

    clear_assignments(context, membership, membership.user_1.username, "user")
    clear_assignments(context, membership, membership.user_2.username, "user")
    clear_assignments(context, membership, membership.user_3.username, "user")

    create_role_assignment(
        context,
        membership.user_1.username,
        "user",
        membership.project_a.project_id,
        "project",
        "project_owner",
    )
    create_role_assignment(
        context,
        membership.user_2.username,
        "user",
        membership.project_b.project_id,
        "project",
        "project_owner",
    )

    delete_role_assignment(
        context,
        membership.user_1.username,
        "user",
        membership.project_a.project_id,
        "project",
    )
    assert is_assigned(context, membership.user_1, membership.project_a) is False

    delete_role_assignment(
        context,
        membership.user_2.username,
        "user",
        membership.project_b.project_id,
        "project",
    )
    assert is_assigned(context, membership.user_2, membership.project_b) is False


def test_projects_membership_project_disabled(context, membership):
    """
    disable project and assign user. user should not be assigned project.
    """

    clear_assignments(context, membership, membership.user_1.username, "user")
    clear_assignments(context, membership, membership.user_2.username, "user")
    clear_assignments(context, membership, membership.user_3.username, "user")

    disable_project(context, membership.project_a)

    create_role_assignment(
        context,
        membership.user_1.username,
        "user",
        membership.project_a.project_id,
        "project",
        "project_owner",
    )
    assert is_assigned(context, membership.user_1, membership.project_a) is False

    disable_project(context, membership.project_b)

    create_role_assignment(
        context,
        membership.user_2.username,
        "user",
        membership.project_b.project_id,
        "project",
        "project_owner",
    )
    assert is_assigned(context, membership.user_2, membership.project_b) is False


def test_projects_membership_project_enabled(context, membership):
    """
    assign user, enable project and check if existing group members are part of project
    """

    clear_assignments(context, membership, membership.user_1.username, "user")
    clear_assignments(context, membership, membership.user_2.username, "user")
    clear_assignments(context, membership, membership.user_3.username, "user")

    create_role_assignment(
        context,
        membership.user_1.username,
        "user",
        membership.project_a.project_id,
        "project",
        "project_owner",
    )
    create_role_assignment(
        context,
        membership.user_2.username,
        "user",
        membership.project_a.project_id,
        "project",
        "project_member",
    )
    create_role_assignment(
        context,
        membership.user_3.username,
        "user",
        membership.project_a.project_id,
        "project",
        "project_member",
    )

    enable_project(context, membership.project_a)

    assert is_assigned(context, membership.user_1, membership.project_a) is True
    assert is_assigned(context, membership.user_2, membership.project_a) is True
    assert is_assigned(context, membership.user_3, membership.project_a) is True


def test_projects_membership_multiple_projects(context, membership, monkeypatch):
    """
    assign user to multiple projects. check for assignments for all
    """

    clear_assignments(context, membership, membership.user_1.username, "user")
    clear_assignments(context, membership, membership.user_2.username, "user")
    clear_assignments(context, membership, membership.user_3.username, "user")

    enable_project(context, membership.project_a)
    enable_project(context, membership.project_b)

    create_role_assignment(
        context,
        membership.user_1.username,
        "user",
        membership.project_a.project_id,
        "project",
        "project_owner",
    )
    create_role_assignment(
        context,
        membership.user_1.username,
        "user",
        membership.project_b.project_id,
        "project",
        "project_owner",
    )

    assert is_assigned(context, membership.user_1, membership.project_a) is True
    assert is_assigned(context, membership.user_1, membership.project_b) is True


def test_projects_get_user_projects(context, membership):
    """
    get user projects
    """

    clear_assignments(context, membership, membership.user_1.username, "user")
    clear_assignments(context, membership, membership.user_2.username, "user")
    clear_assignments(context, membership, membership.user_3.username, "user")

    enable_project(context, membership.project_a)
    enable_project(context, membership.project_b)

    create_role_assignment(
        context,
        membership.user_1.username,
        "user",
        membership.project_a.project_id,
        "project",
        "project_owner",
    )
    create_role_assignment(
        context,
        membership.user_2.username,
        "user",
        membership.project_b.project_id,
        "project",
        "project_owner",
    )
    create_role_assignment(
        context,
        membership.user_3.username,
        "user",
        membership.project_a.project_id,
        "project",
        "project_member",
    )
    create_role_assignment(
        context,
        membership.user_3.username,
        "user",
        membership.project_b.project_id,
        "project",
        "project_member",
    )

    def check_user_projects(username: str, project_ids: List[str]):
        result = context.projects.get_user_projects(
            GetUserProjectsRequest(username=username)
        )

        assert result.projects is not None
        count = 0
        for project in result.projects:
            if project.project_id in project_ids:
                count += 1

        assert len(project_ids) == count

    check_user_projects(
        username=membership.user_1.username,
        project_ids=[membership.project_a.project_id],
    )
    assert is_assigned(context, membership.user_1, membership.project_b) is False

    check_user_projects(
        username=membership.user_2.username,
        project_ids=[membership.project_b.project_id],
    )
    assert is_assigned(context, membership.user_2, membership.project_a) is False

    check_user_projects(
        username=membership.user_3.username,
        project_ids=[membership.project_a.project_id, membership.project_b.project_id],
    )

    context.accounts.disable_user(membership.user_3.username)
    check_user_projects(username=membership.user_3.username, project_ids=[])
    assert is_assigned(context, membership.user_3, membership.project_a) is False

    context.accounts.enable_user(membership.user_3.username)
    check_user_projects(
        username=membership.user_3.username,
        project_ids=[membership.project_a.project_id, membership.project_b.project_id],
    )
    assert is_assigned(context, membership.user_3, membership.project_a) is True


def test_projects_get_user_projects_invalid_input_username(context, membership):
    """
    get user projects - invalid characters in username
    """

    enable_project(context, membership.project_a)

    with pytest.raises(exceptions.SocaException) as excinfo:
        context.projects.get_user_projects(
            GetUserProjectsRequest(username="\u2460\u2461\u2462\u2463")
        )
    assert excinfo.value.error_code == errorcodes.INVALID_PARAMS
    assert excinfo.value.message == constants.USERNAME_ERROR_MESSAGE


def test_projects_delete_group(context, membership):
    """
    delete group
    """

    clear_assignments(context, membership, membership.user_1.username, "user")
    clear_assignments(context, membership, membership.user_2.username, "user")
    clear_assignments(context, membership, membership.user_3.username, "user")

    clear_assignments(context, membership, membership.group_a1.name, "group")
    clear_assignments(context, membership, membership.group_a2.name, "group")
    clear_assignments(context, membership, membership.group_b.name, "group")

    create_role_assignment(
        context,
        membership.user_1.username,
        "user",
        membership.project_a.project_id,
        "project",
        "project_owner",
    )
    assert is_assigned(context, membership.user_1, membership.project_a) is True

    context.accounts.delete_group(group_name=membership.group_a1.name, force=True)
    # Ensure user has access to project_a through group_a2 after deletion of group_a1
    assert is_assigned(context, membership.user_1, membership.project_a) is True

    create_role_assignment(
        context,
        membership.user_2.username,
        "user",
        membership.project_b.project_id,
        "project",
        "project_owner",
    )
    assert is_assigned(context, membership.user_2, membership.project_b) is True

    # context.accounts.delete_group(group_name=membership.group_b.name, force=True)
    # # Ensure user does not have access to project after deletion of group_b
    # assert is_assigned(context, membership.user_2, membership.project_b) is False
