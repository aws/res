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

__all__ = (
    'IdeaNagSuppression',
    'SocaBaseConstruct'
)

from ideadatamodel import exceptions, errorcodes, constants, SocaBaseModel
from ideasdk.utils import Utils
import ideaadministrator
from ideaadministrator.app_context import AdministratorContext

from typing import Optional, List
import aws_cdk as cdk
import constructs
from aws_cdk import (
    aws_iam as iam
)
from cdk_nag import NagSuppressions


class IdeaNagSuppression(SocaBaseModel):
    rule_id: str
    reason: str


class SocaBaseConstruct:

    def __init__(self, context: AdministratorContext, name: str, scope: constructs.IConstruct = None, **kwargs):
        self.context = context
        self._name = name
        self._construct_id: Optional[str] = self.get_construct_id()
        self.kwargs = kwargs
        if scope:
            super().__init__(scope, self.construct_id, **kwargs)
            self.add_common_tags()

    @property
    def has_tags(self) -> bool:
        return self.kwargs is not None and 'tags' in self.kwargs

    @property
    def cluster_name(self) -> str:
        return self.context.config().get_string('cluster.cluster_name', required=True)

    @property
    def release_version(self) -> str:
        return ideaadministrator.__version__

    @property
    def construct_id_prefix(self) -> str:
        return f'{self.cluster_name}'

    @property
    def resource_name_prefix(self) -> str:
        return f'{self.cluster_name}'

    @property
    def construct_id(self) -> str:
        return self._construct_id

    @property
    def name(self) -> str:
        if Utils.is_empty(self._name):
            raise exceptions.SocaException(
                error_code=errorcodes.GENERAL_ERROR,
                message='Invalid CDK Construct. "name" is required.'
            )
        return self._name

    @property
    def resource_name(self) -> str:
        return self.build_resource_name(self.name)

    def name_title_case(self):
        return Utils.to_title_case(self.name)

    @property
    def aws_account_arn(self) -> str:
        aws_partition = self.context.config().get_string('cluster.aws.partition', required=True)
        aws_account_id = self.context.config().get_string('cluster.aws.account_id', required=True)
        return f'arn:{aws_partition}:*:*:{aws_account_id}:*'

    @staticmethod
    def build_service_principal(service_name) -> iam.ServicePrincipal:
        service_fqdn = f'{service_name}.{cdk.Aws.URL_SUFFIX}'
        return iam.ServicePrincipal(service_fqdn)

    # override if required
    def get_construct_id(self) -> Optional[str]:
        return self.name

    # trimmed format - {prefix}-{region}-{name[:10]}-{hash}
    def build_trimmed_resource_name(self, name: str, region_suffix=False, trim_length=64) -> str:
        prefix = self.resource_name_prefix
        suffix = ''
        if region_suffix:
            suffix = f'-{self.context.config().get_string("cluster.aws.region", required=True)}'

        resource_name = f'{prefix}-{name}{suffix}'
        trimmed_resource_name = f'{prefix}{suffix}-{name[:10]}-{Utils.shake_256(data=resource_name, num_bytes=int((trim_length - 12 - len(prefix) - len(suffix)) / 2))}'
        return trimmed_resource_name

    def build_resource_name(self, name: str, region_suffix=False) -> str:
        prefix = self.resource_name_prefix
        resource_name = f'{prefix}-{name}'
        if region_suffix:
            aws_region = self.context.config().get_string('cluster.aws.region', required=True)
            resource_name = f'{resource_name}-{aws_region}'
        return resource_name

    def add_common_tags(self, construct: Optional[constructs.IConstruct] = None):
        if construct is None and isinstance(self, constructs.Construct):
            construct = self
        cdk.Tags.of(construct).add(constants.IDEA_TAG_NAME, self.resource_name)
        cdk.Tags.of(construct).add(constants.IDEA_TAG_ENVIRONMENT_NAME, self.cluster_name)

    def add_backup_tags(self, construct: Optional[constructs.IConstruct] = None):
        """
        add AWS Backup integration tags.
        backup tags cannot be added as a blanket tag on CFN template or common tags.
        only specific resources that need backup integration must be tagged.
        """
        if construct is None and isinstance(self, constructs.Construct):
            construct = self
        cdk.Tags.of(construct).add(constants.IDEA_TAG_BACKUP_PLAN, f'{self.cluster_name}-{constants.MODULE_CLUSTER}')

    def build_instance_profile_arn(self, instance_profile_ref: str):
        aws_partition = self.context.config().get_string('cluster.aws.partition', required=True)
        aws_account_id = self.context.config().get_string('cluster.aws.account_id', required=True)
        return f'arn:{aws_partition}:iam::{aws_account_id}:instance-profile/{instance_profile_ref}'

    def is_ds_activedirectory(self) -> bool:
        return self.context.config().get_string('directoryservice.provider') in (constants.DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY,
                                                                                 constants.DIRECTORYSERVICE_ACTIVE_DIRECTORY)

    def is_ds_openldap(self) -> bool:
        return self.context.config().get_string('directoryservice.provider') == constants.DIRECTORYSERVICE_OPENLDAP

    def add_nag_suppression(self, suppressions: List[IdeaNagSuppression], construct: constructs.IConstruct = None, apply_to_children: bool = False):
        if construct is None:
            construct = self
        cdk_nag_suppressions = []
        for suppression in suppressions:
            cdk_nag_suppressions.append({
                'id': suppression.rule_id,
                'reason': suppression.reason
            })
        if isinstance(construct, cdk.Stack):
            NagSuppressions.add_stack_suppressions(
                stack=construct,
                suppressions=cdk_nag_suppressions,
                apply_to_nested_stacks=apply_to_children
            )
        else:
            NagSuppressions.add_resource_suppressions(
                construct=construct,
                suppressions=cdk_nag_suppressions,
                apply_to_children=apply_to_children
            )

    def get_kms_key_arn(self, key_id: str) -> str:
        # arn:AWS_PARTITION:kms:AWS_REGION:ACCOUNT_ID:key/UUID
        if key_id.startswith('arn:'):
            return key_id
        aws_partition = self.context.config().get_string('cluster.aws.partition', required=True)
        aws_region = self.context.config().get_string('cluster.aws.region', required=True)
        aws_account_id = self.context.config().get_string('cluster.aws.account_id', required=True)
        return f'arn:{aws_partition}:kms:{aws_region}:{aws_account_id}:key/{key_id}'

    def add_retain_on_delete(self, construct: constructs.IConstruct = None):
        if construct is None and isinstance(self, constructs.Construct):
            construct = self
        construct.node.find_child('Resource').cfn_options.deletion_policy = cdk.CfnDeletionPolicy.RETAIN
