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

import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideaclustermanager import AppContext
from ideaclustermanager.app.accounts.account_tasks import GroupMembershipUpdatedTask
from ideaclustermanager.app.projects.project_tasks import (
    ProjectDisabledTask,
    ProjectEnabledTask,
)

from ideadatamodel import (
    CreateProjectRequest,
    DeleteProjectRequest,
    DisableProjectRequest,
    EnableProjectRequest,
    GetProjectRequest,
    GetUserProjectsRequest,
    Group,
    ListProjectsRequest,
    Project,
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


def enable_project(context: AppContext, project: Project):
    context.projects.enable_project(EnableProjectRequest(project_id=project.project_id))
    task = ProjectEnabledTask(context=context)
    task.invoke({"project_id": project.project_id})


def disable_project(context: AppContext, project: Project):
    context.projects.disable_project(
        EnableProjectRequest(project_id=project.project_id)
    )
    task = ProjectDisabledTask(context=context)
    task.invoke({"project_id": project.project_id})


def is_memberof(context: AppContext, user: User, project: Project) -> bool:
    result = context.projects.get_user_projects(
        GetUserProjectsRequest(username=user.username)
    )

    if result.projects is None:
        return False

    for user_project in result.projects:
        if user_project.project_id == project.project_id:
            return True

    return False


def add_member(context: AppContext, user: User, project: Project):
    username = user.username
    for group_name in project.ldap_groups:
        context.accounts.add_users_to_group(usernames=[username], group_name=group_name)
        task = GroupMembershipUpdatedTask(context=context)
        task.invoke(
            payload={"group_name": group_name, "username": username, "operation": "add"}
        )


def remove_member(context: AppContext, user: User, project: Project):
    username = user.username
    for group_name in project.ldap_groups:
        context.accounts.remove_users_from_group(
            usernames=[username], group_name=group_name
        )
        task = GroupMembershipUpdatedTask(context=context)
        task.invoke(
            payload={
                "group_name": group_name,
                "username": username,
                "operation": "remove",
            }
        )


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

    def create_group(group_name: str) -> Group:
        group = context.accounts.create_group(
            Group(
                title=f"{group_name} Project Group",
                name=f"{group_name}-project-group",
                group_type=constants.GROUP_TYPE_PROJECT,
            )
        )
        assert group is not None
        return group

    def create_project(
        project_name: str, project_title: str, group_names: List[str], users=[]
    ) -> Project:
        # create project
        result = context.projects.create_project(
            CreateProjectRequest(
                project=Project(
                    name=project_name,
                    title=project_title,
                    ldap_groups=group_names,
                    users=users,
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
    project_a = create_project("project-a", "Project A", [group_a1.name, group_a2.name])
    project_b = create_project("project-b", "Project B", [group_b.name])
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
    group = context.accounts.create_group(
        Group(
            title=f"Sample Project Group",
            name=f"sample-project-group",
            group_type=constants.GROUP_TYPE_PROJECT,
        )
    )

    assert group is not None

    result = context.projects.create_project(
        CreateProjectRequest(
            project=Project(
                name="sampleproject",
                title="Sample Project",
                description="Sample Project Description",
                ldap_groups=["sample-project-group"],
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
    assert result.project.name == "sampleproject"
    ProjectsTestContext.crud_project = result.project

    result = context.projects.get_project(
        GetProjectRequest(project_name=ProjectsTestContext.crud_project.name)
    )
    assert result is not None
    assert result.project is not None
    assert result.project.enabled is True
    assert result.project.ldap_groups is not None
    assert (
        result.project.ldap_groups[0] == ProjectsTestContext.crud_project.ldap_groups[0]
    )
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
    add_member(context, membership.user_1, ProjectsTestContext.crud_project)
    enable_project(context, ProjectsTestContext.crud_project)
    assert is_memberof(context, membership.user_1, ProjectsTestContext.crud_project)

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
    for group in ProjectsTestContext.crud_project.ldap_groups:
        projects = context.projects.user_projects_dao.get_projects_by_group_name(group)
        assert len(projects) > 0

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

    # Project should have been removed from the project-groups table
    for group in ProjectsTestContext.crud_project.ldap_groups:
        projects = context.projects.user_projects_dao.get_projects_by_group_name(group)
        assert len(projects) == 0

    # Project should have been removed from the user-project table
    projects = context.projects.user_projects_dao.get_projects_by_username(
        membership.user_1.username
    )
    assert len(projects) == 0


def test_projects_membership_setup(context, membership):
    """
    check if membership setup data is valid and tests are starting with a clean slate.
    """

    assert membership.project_a is not None
    assert membership.project_b is not None
    assert membership.user_1 is not None
    assert membership.user_2 is not None
    assert membership.user_3 is not None

    assert is_memberof(context, membership.user_1, membership.project_a) is False
    assert is_memberof(context, membership.user_2, membership.project_a) is False
    assert is_memberof(context, membership.user_3, membership.project_a) is False

    assert is_memberof(context, membership.user_1, membership.project_b) is False
    assert is_memberof(context, membership.user_2, membership.project_b) is False
    assert is_memberof(context, membership.user_3, membership.project_b) is False


def test_projects_membership_member_added(context, membership):
    """
    add user to a group and check if user is member of projects
    """

    add_member(context, membership.user_1, membership.project_a)
    assert is_memberof(context, membership.user_1, membership.project_a) is True

    add_member(context, membership.user_2, membership.project_b)
    assert is_memberof(context, membership.user_2, membership.project_b) is True


def test_projects_membership_member_removed(context, membership, monkeypatch):
    """
    add user to a group and check if user is member of projects
    """

    monkeypatch.setattr(context.ldap_client, "is_readonly", lambda: True)

    remove_member(context, membership.user_1, membership.project_a)
    assert is_memberof(context, membership.user_1, membership.project_a) is False

    remove_member(context, membership.user_2, membership.project_b)
    assert is_memberof(context, membership.user_2, membership.project_b) is False


def test_projects_membership_project_disabled(context, membership):
    """
    disable project and add member. user should not be member of project.
    """

    disable_project(context, membership.project_a)

    add_member(context, membership.user_1, membership.project_a)
    assert is_memberof(context, membership.user_1, membership.project_a) is False

    disable_project(context, membership.project_b)

    add_member(context, membership.user_2, membership.project_b)
    assert is_memberof(context, membership.user_2, membership.project_b) is False


def test_projects_membership_project_enabled(context, membership):
    """
    add member, enable project and check if existing group members are part of project
    """

    add_member(context, membership.user_1, membership.project_a)
    add_member(context, membership.user_2, membership.project_a)
    add_member(context, membership.user_3, membership.project_a)

    enable_project(context, membership.project_a)

    assert is_memberof(context, membership.user_1, membership.project_a) is True
    assert is_memberof(context, membership.user_2, membership.project_a) is True
    assert is_memberof(context, membership.user_3, membership.project_a) is True


def clear_memberships(context: AppContext, membership, user: User):
    remove_member(context, user, membership.project_a)
    remove_member(context, user, membership.project_b)


def test_projects_membership_multiple_projects(context, membership, monkeypatch):
    """
    add user to multiple projects. check for membership for all
    """

    monkeypatch.setattr(context.ldap_client, "is_readonly", lambda: True)

    # pre-requisites
    clear_memberships(context, membership, membership.user_1)
    clear_memberships(context, membership, membership.user_2)
    clear_memberships(context, membership, membership.user_3)

    enable_project(context, membership.project_a)
    enable_project(context, membership.project_b)

    add_member(context, membership.user_1, membership.project_a)
    add_member(context, membership.user_1, membership.project_b)

    assert is_memberof(context, membership.user_1, membership.project_a) is True
    assert is_memberof(context, membership.user_1, membership.project_b) is True


def test_projects_get_user_projects(context, membership):
    """
    get user projects
    """

    clear_memberships(context, membership, membership.user_1)
    clear_memberships(context, membership, membership.user_2)
    clear_memberships(context, membership, membership.user_3)

    enable_project(context, membership.project_a)
    enable_project(context, membership.project_b)

    add_member(context, membership.user_1, membership.project_a)

    add_member(context, membership.user_2, membership.project_b)

    add_member(context, membership.user_3, membership.project_a)
    add_member(context, membership.user_3, membership.project_b)

    # verify

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
    assert is_memberof(context, membership.user_1, membership.project_b) is False

    check_user_projects(
        username=membership.user_2.username,
        project_ids=[membership.project_b.project_id],
    )
    assert is_memberof(context, membership.user_2, membership.project_a) is False

    check_user_projects(
        username=membership.user_3.username,
        project_ids=[membership.project_a.project_id, membership.project_b.project_id],
    )

    context.accounts.disable_user(membership.user_3.username)
    check_user_projects(username=membership.user_3.username, project_ids=[])
    assert is_memberof(context, membership.user_3, membership.project_a) is False

    context.accounts.enable_user(membership.user_3.username)
    check_user_projects(
        username=membership.user_3.username,
        project_ids=[membership.project_a.project_id, membership.project_b.project_id],
    )
    assert is_memberof(context, membership.user_3, membership.project_a) is True


def test_projects_delete_group(context, membership):
    """
    delete group
    """

    clear_memberships(context, membership, membership.user_1)
    clear_memberships(context, membership, membership.user_2)
    clear_memberships(context, membership, membership.user_3)

    add_member(context, membership.user_1, membership.project_a)
    assert is_memberof(context, membership.user_1, membership.project_a) is True

    context.accounts.delete_group(group_name=membership.group_a1.name, force=True)
    # Ensure user has access to project_a through group_a2 after deletion of group_a1
    assert is_memberof(context, membership.user_1, membership.project_a) is True

    add_member(context, membership.user_2, membership.project_b)
    assert is_memberof(context, membership.user_2, membership.project_b) is True

    context.accounts.delete_group(group_name=membership.group_b.name, force=True)
    # Ensure user does not have access to project after deletion of group_b
    assert is_memberof(context, membership.user_2, membership.project_b) is False
