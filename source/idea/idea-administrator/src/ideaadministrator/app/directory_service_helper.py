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

from ideasdk.utils import Utils
from ideasdk.context import SocaCliContext, SocaContextOptions
from ideadatamodel import constants

from typing import Dict


class DirectoryServiceHelper:
    """
    Helper class for Directory Service related functionality.
    """

    def __init__(self, cluster_name: str, aws_region: str, aws_profile: str = None):
        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.aws_profile = aws_profile

    def create_service_account_secrets(self, username: str, password: str, purpose: str, kms_key_id: str = None) -> Dict:
        """
        In order to use an existing AWS Managed Active Directory (or even in case of an On-Prem or Self-Managed AD),
        cluster manager needs to have access to the service account credentials.

        this method helps admins to create the service account credentials as secrets in AWS Secrets manager, with
        appropriate Tags such that cluster manager is authorized to access these credentials via IAM policies

        Note:
        * This method is expected to be invoked prior to creation of the cluster or any configuration updates to cluster config db.
        * For that reason, context is not initialized in the constructor and cluster_name is not passed to the context options.

        :param str username: username of the account
        :param str password: password of the account
        :param str purpose: the purpose/title of the account
        :param str kms_key_id: the customer managed kms encryption key that you plan to use for secrets manager
        """

        context = SocaCliContext(
            options=SocaContextOptions(
                aws_region=self.aws_region,
                aws_profile=self.aws_profile,
                enable_aws_client_provider=True,
                enable_iam_permission_util=True
            )
        )

        tags = Utils.convert_tags_dict_to_aws_tags({
            constants.IDEA_TAG_ENVIRONMENT_NAME: self.cluster_name,
            constants.IDEA_TAG_MODULE_NAME: constants.MODULE_DIRECTORYSERVICE,
            constants.IDEA_TAG_MODULE_ID: constants.MODULE_DIRECTORYSERVICE
        })

        # create username secret
        create_username_secret_request = {
            'Name': f'{self.cluster_name}-{constants.MODULE_DIRECTORYSERVICE}-{purpose}-username',
            'Description': f'DirectoryService {purpose} username, Cluster: {self.cluster_name}',
            'SecretString': username,
            'Tags': tags
        }
        if Utils.is_not_empty(kms_key_id):
            create_username_secret_request['KmsKeyId'] = kms_key_id
        # This can produce exception from AWS API for duplicate secret
        create_username_secret_result = context.aws().secretsmanager().create_secret(**create_username_secret_request)
        username_secret_arn = Utils.get_value_as_string('ARN', create_username_secret_result)

        # create password secret
        create_password_secret_request = {
            'Name': f'{self.cluster_name}-{constants.MODULE_DIRECTORYSERVICE}-{purpose}-password',
            'Description': f'DirectoryService {purpose} password, Cluster: {self.cluster_name}',
            'SecretString': password,
            'Tags': tags
        }
        if Utils.is_not_empty(kms_key_id):
            create_password_secret_request['KmsKeyId'] = kms_key_id
        # This can produce exception from AWS API for duplicate secret
        create_password_secret_result = context.aws().secretsmanager().create_secret(**create_password_secret_request)
        password_secret_arn = Utils.get_value_as_string('ARN', create_password_secret_result)

        return {
            'username_secret_arn': username_secret_arn,
            'password_secret_arn': password_secret_arn
        }
