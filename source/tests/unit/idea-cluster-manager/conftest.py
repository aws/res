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

import time
from unittest.mock import MagicMock

import boto3
import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideaclustermanager import AppContext
from ideaclustermanager.app.accounts.accounts_service import AccountsService
from ideaclustermanager.app.accounts.cognito_user_pool import (
    CognitoUserPool,
    CognitoUserPoolOptions,
)
from ideaclustermanager.app.auth.api_authorization_service import (
    ClusterManagerApiAuthorizationService,
)
from ideaclustermanager.app.authz.role_assignments_service import RoleAssignmentsService
from ideaclustermanager.app.authz.roles_service import RolesService
from ideaclustermanager.app.projects.projects_service import ProjectsService
from ideaclustermanager.app.shared_filesystem.shared_filesystem_service import (
    SharedFilesystemService,
)
from ideaclustermanager.app.snapshots.snapshots_service import SnapshotsService
from ideaclustermanager.app.tasks.task_manager import TaskManager
from ideasdk.auth import TokenService, TokenServiceOptions
from ideasdk.aws import AwsClientProvider, AWSUtil, EC2InstanceTypesDB
from ideasdk.client.evdi_client import EvdiClient
from ideasdk.context import SocaContextOptions
from ideasdk.utils import GroupNameHelper, Utils
from ideatestutils import IdeaTestProps, MockConfig, MockInstanceTypes
from ideatestutils.dynamodb.dynamodb_local import DynamoDBLocal
from mock_ldap_client import MockLdapClient
from mock_vdc_client import MockVirtualDesktopControllerClient

from ideadatamodel import SocaAnyPayload

# initialize monkey patch globally, so that it can be used inside session scoped context fixtures
# this allows session scoped monkey patches to be applicable across all unit tests
# monkeypatch.undo() is called at the end of context fixture
monkeypatch = MonkeyPatch()


@pytest.fixture(scope="session")
def ddb_local():
    ddb_local = DynamoDBLocal(db_name="cluster-manager", reset=True)
    ddb_local.start()

    # wait for ddb local server to start ...
    time.sleep(1)

    yield ddb_local

    ddb_local.stop()


@pytest.fixture(scope="session")
def context(ddb_local):
    """
    fixture to initialize context with mock config and aws clients
    goal is to ensure no network request are executed while executing unit tests
    """

    print("initializing cluster-manager context ...")

    def mock_function(*_, **__):
        return {}

    mock_boto_session = SocaAnyPayload()
    mock_boto_session.region_name = "us-east-1"
    mock_boto_session.client = mock_function

    mock_ec2_client = SocaAnyPayload()
    mock_ec2_client.describe_security_groups = mock_function
    mock_ec2_client.authorize_security_group_egress = MagicMock(
        return_value="egress created"
    )
    mock_ec2_client.revoke_security_group_egress = MagicMock(
        return_value="egress deleted"
    )
    mock_ec2_client.describe_instances = MagicMock(
        return_value={"Reservations": [{"Instances": [{"InstanceId": "i-123"}]}]}
    )

    mock_s3_client = SocaAnyPayload()
    mock_s3_client.upload_file = mock_function
    mock_s3_client.get_bucket_acl = mock_function
    mock_s3_client.put_object = mock_function()
    mock_s3_client.get_object = mock_function()

    mock_cognito_idp = SocaAnyPayload()
    mock_cognito_idp.admin_create_user = mock_function
    mock_cognito_idp.admin_remove_user_from_group = mock_function
    mock_cognito_idp.admin_delete_user = mock_function
    mock_cognito_idp.admin_add_user_to_group = mock_function
    mock_cognito_idp.admin_get_user = mock_function
    mock_cognito_idp.admin_set_user_password = mock_function
    mock_cognito_idp.admin_update_user_attributes = mock_function
    mock_cognito_idp.admin_enable_user = mock_function
    mock_cognito_idp.admin_disable_user = mock_function
    mock_cognito_idp.describe_password_policy = mock_function
    mock_cognito_idp.describe_user_pool = mock_function
    mock_cognito_idp.update_identity_provider = MagicMock(return_value="idp updated")
    mock_cognito_idp.create_identity_provider = MagicMock(return_value="idp created")
    mock_cognito_idp.delete_identity_provider = MagicMock(return_value="idp deleted")
    mock_cognito_idp.update_user_pool_client = MagicMock(
        return_value={
            "UserPoolClient": {"ClientId": "test-id", "ClientSecret": "test-secret"}
        }
    )
    mock_cognito_idp.create_user_pool_client = MagicMock(
        return_value={
            "UserPoolClient": {"ClientId": "test-id", "ClientSecret": "test-secret"}
        }
    )
    mock_cognito_idp.list_users = MagicMock(
        return_value={
            "Users": [
                {
                    "UserStatus": "CONFIRMED",
                    "Username": "clusteradmin",
                    "Attributes": [
                        {"Name": "email", "Value": "clusteradmin@user"},
                        {"Name": "identities", "Value": []},
                    ],
                },
                {
                    "UserStatus": "EXTERNAL_PROVIDER",
                    "Username": "external",
                    "Attributes": [
                        {"Name": "email", "Value": "external@user"},
                        {"Name": "identities", "Value": ["test-provider"]},
                    ],
                },
                {
                    "UserStatus": "CONFIRMED",
                    "Username": "linked",
                    "Attributes": [
                        {"Name": "email", "Value": "linked@user"},
                        {"Name": "identities", "Value": ["test-provier"]},
                    ],
                },
                {
                    "UserStatus": "CONFIRMED",
                    "Username": "unlinked",
                    "Attributes": [
                        {"Name": "email", "Value": "unlinked@user"},
                        {"Name": "identities", "Value": []},
                    ],
                },
            ]
        }
    )
    mock_cognito_idp.admin_link_provider_for_user = MagicMock()
    mock_cognito_idp.get_identity_provider_by_identifier = MagicMock(
        return_value={"IdentityProvider": None}
    )

    mock_elbv2 = SocaAnyPayload()
    mock_elbv2.describe_target_groups = MagicMock(
        return_value={
            "TargetGroups": [
                {
                    "TargetGroupArn": "target-group-arn",
                    "TargetGroupName": "target-group-name",
                    "VpcId": "target-group-vpc-id",
                }
            ]
        }
    )
    mock_elbv2.describe_listeners = MagicMock(
        return_value={"Listeners": [{"ListenerArn": "listener-arn"}]}
    )
    mock_elbv2.delete_listener = MagicMock(return_value="listener deleted")
    mock_elbv2.delete_target_group = MagicMock(return_value="target group deleted")
    mock_elbv2.create_listener = MagicMock(
        return_value={"Listeners": [{"ListenerArn": "listener-arn"}]}
    )
    mock_elbv2.create_target_group = MagicMock(
        return_value={
            "TargetGroups": [
                {
                    "TargetGroupArn": "target-group-arn",
                    "TargetGroupName": "target-group-name",
                    "VpcId": "target-group-vpc-id",
                }
            ]
        }
    )
    mock_elbv2.register_targets = MagicMock(return_value="registered target")

    mock_secrets_manager = SocaAnyPayload()
    mock_secrets_manager.describe_secret = MagicMock(return_value=None)
    mock_secrets_manager.create_secret = MagicMock(return_value={"ARN": "secret-arn"})
    mock_secrets_manager.update_secret = MagicMock(return_value={"ARN": "secret-arn"})

    mock_efs = SocaAnyPayload()
    mock_efs.describe_file_systems = MagicMock(return_value={"FileSystems": []})

    mock_fsx = SocaAnyPayload()
    mock_fsx.describe_file_systems = MagicMock(
        return_value={
            "FileSystems": [
                {
                    "FileSystemType": "LUSTRE",
                    "Lifecycle": "AVAILABLE",
                    "FileSystemId": "lustre_filesystem_id",
                    "SubnetIds": ["subnet_id"],
                }
            ]
        }
    )

    monkeypatch.setattr(
        EC2InstanceTypesDB,
        "_instance_type_names_from_botocore",
        MockInstanceTypes.get_instance_type_names,
    )
    monkeypatch.setattr(EvdiClient, "publish_user_disabled_event", mock_function)

    def create_mock_boto_session(**_):
        return boto3.Session(
            aws_access_key_id="mock_access_key",
            aws_secret_access_key="mock_secret_access_key",
            region_name="us-east-1",
        )

    monkeypatch.setattr(Utils, "create_boto_session", create_mock_boto_session)
    monkeypatch.setattr(
        AWSUtil, "get_ec2_instance_type", MockInstanceTypes.get_instance_type
    )
    monkeypatch.setattr(AwsClientProvider, "s3", lambda *_: mock_s3_client)
    monkeypatch.setattr(AwsClientProvider, "ec2", lambda *_: mock_ec2_client)
    monkeypatch.setattr(AwsClientProvider, "cognito_idp", lambda *_: mock_cognito_idp)
    monkeypatch.setattr(
        AwsClientProvider, "secretsmanager", lambda *_: mock_secrets_manager
    )
    monkeypatch.setattr(AwsClientProvider, "efs", lambda *_: mock_efs)
    monkeypatch.setattr(AwsClientProvider, "fsx", lambda *_: mock_fsx)
    monkeypatch.setattr(AwsClientProvider, "elbv2", lambda *_: mock_elbv2)

    mock_config = MockConfig()

    test_props = IdeaTestProps()

    monkeypatch.setenv("RES_DEV_MODE", "true")

    test_dir = test_props.get_test_dir("cluster-manager-tests")
    monkeypatch.setenv("IDEA_APP_DEPLOY_DIR", test_dir)

    context = AppContext(
        options=SocaContextOptions(
            cluster_name="idea-mock",
            module_id="cluster-manager",
            module_name="cluster-manager",
            module_set="default",
            enable_aws_client_provider=True,
            enable_aws_util=True,
            use_vpc_endpoints=True,
            config=mock_config.get_config(),
        )
    )
    context._config.get_module_id = MagicMock(return_value="IdentityProvider")
    context._config.db = MagicMock(set_config_entry=MagicMock())
    context.task_manager = TaskManager(context=context, tasks=[])
    monkeypatch.setattr(
        context.task_manager,
        "send",
        lambda *args, **kwargs: print(
            f"[TaskManager.send()] args: {args}, kwargs: {kwargs}"
        ),
    )

    context.ldap_client = MockLdapClient(context=context)
    context.user_pool = CognitoUserPool(
        context=context,
        options=CognitoUserPoolOptions(
            user_pool_id=context.config().get_string(
                "identity-provider.cognito.user_pool_id", required=True
            ),
            admin_group_name=context.config().get_string(
                "identity-provider.cognito.administrators_group_name", required=True
            ),
            client_id="mock-client-id",
            client_secret="mock-client-secret",
        ),
    )

    context.token_service = TokenService(
        context=context,
        options=TokenServiceOptions(
            cognito_user_pool_provider_url=context.config().get_string(
                "identity-provider.cognito.provider_url", required=True
            ),
            cognito_user_pool_domain_url=context.config().get_string(
                "identity-provider.cognito.domain_url", required=True
            ),
            client_id="mock-client-id",
            client_secret="mock-client-secret",
            client_credentials_scope=[],
        ),
    )

    context.accounts = AccountsService(
        context=context,
        ldap_client=context.ldap_client,
        user_pool=context.user_pool,
        evdi_client=EvdiClient(context=context),
        task_manager=context.task_manager,
        token_service=context.token_service,
    )
    context.accounts.create_defaults()

    context.roles = RolesService(
        context=context,
    )
    context.roles.create_defaults()

    context.role_assignments = RoleAssignmentsService(
        context=context,
    )

    # api authorization service
    context.api_authorization_service = ClusterManagerApiAuthorizationService(
        accounts=context.accounts,
        roles=context.roles,
        role_assignments=context.role_assignments,
    )

    context.vdc_client = MockVirtualDesktopControllerClient()

    context.projects = ProjectsService(
        context=context,
        accounts_service=context.accounts,
        task_manager=context.task_manager,
        vdc_client=context.vdc_client,
    )

    context.roles = RolesService(context=context)

    context.role_assignments = RoleAssignmentsService(context=context)

    context.snapshots = SnapshotsService(context=context)

    context.shared_filesystem = SharedFilesystemService(context=context)

    yield context

    print("cluster manager context clean-up ...")
    monkeypatch.undo()
