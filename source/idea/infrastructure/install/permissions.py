#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import aws_cdk
from aws_cdk import aws_iam as iam
from constructs import Construct, DependencyGroup

from idea.infrastructure.install.constants import INSTALLER_ECR_REPO_NAME_SUFFIX
from idea.infrastructure.install.installer_permissions.create_permissions import (
    CreatePermissions,
)
from idea.infrastructure.install.installer_permissions.delete_permissions import (
    DeletePermissions,
)
from idea.infrastructure.install.installer_permissions.update_permissions import (
    UpdatePermissions,
)


class Permissions(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        dependency_group: DependencyGroup,
        environment_name: str,
    ):
        super().__init__(scope, id)
        self.environment_name = environment_name
        # TODO: Split role into separate Install/Delete/Update roles to allow for finer grained permissions
        self.pipeline_role = iam.Role(
            self,
            "PipelineRole",
            assumed_by=self.get_principal(),
            role_name=f"Admin-{environment_name}-{aws_cdk.Aws.REGION}-PipelineRole",
        )

        statements = (
            CreatePermissions(environment_name).get_permissions()
            + DeletePermissions(environment_name).get_permissions()
            + UpdatePermissions(environment_name).get_permissions()
        )

        for statement in statements:
            self.pipeline_role.add_to_policy(statement)

        dependency_group.add(self.pipeline_role)

    def get_principal(self) -> iam.ServicePrincipal:
        return iam.ServicePrincipal(
            "ecs-tasks.amazonaws.com",
            conditions={
                "ArnLike": {
                    "aws:SourceArn": f"arn:{aws_cdk.Aws.PARTITION}:ecs:{aws_cdk.Aws.REGION}:{aws_cdk.Aws.ACCOUNT_ID}:*"
                },
                "StringEquals": {"aws:SourceAccount": aws_cdk.Aws.ACCOUNT_ID},
            },
        )
