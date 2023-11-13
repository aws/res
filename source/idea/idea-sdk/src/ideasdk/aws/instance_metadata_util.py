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

from ideasdk.protocols import SocaContextProtocol, InstanceMetadataUtilProtocol
from ideadatamodel import exceptions, errorcodes, EC2InstanceIdentityDocument
from ideasdk.utils import Utils

import requests
from typing import Optional

EC2_INSTANCE_METADATA_LATEST = 'http://169.254.169.254/latest'
EC2_INSTANCE_METADATA_URL_PREFIX = f'{EC2_INSTANCE_METADATA_LATEST}/meta-data'
EC2_INSTANCE_IDENTITY_DOCUMENT_URL = f'{EC2_INSTANCE_METADATA_LATEST}/dynamic/instance-identity/document'

EC2_INSTANCE_METADATA_API_URL = f'{EC2_INSTANCE_METADATA_LATEST}/api'
EC2_IMDS_TOKEN_REQUEST_HEADERS = {'X-aws-ec2-metadata-token-ttl-seconds': '900'}


class InstanceMetadataUtil(InstanceMetadataUtilProtocol):
    """
    Utils for EC2 instance metadata
    """
    def get_imds_auth_token(self) -> str:
        """
        Generate an IMDSv2 auth token from EC2 instance metadata
        """
        try:
            result = requests.put(EC2_INSTANCE_METADATA_API_URL + '/token', headers=EC2_IMDS_TOKEN_REQUEST_HEADERS)
            if result.status_code != 200:
                raise exceptions.SocaException(
                    error_code=errorcodes.EC2_INSTANCE_METADATA_FAILED,
                    message=f'Failed to retrieve EC2 instance IMDSv2 authentication token. Statuscode: ({result.status_code})'
                )
            else:
                return result.text.strip()
        except Exception as e:
            raise e

    def get_imds_auth_header(self) -> dict:
        """
        Return a built auth header for EC2 instance metadata IMDSv2
        """
        return {'X-aws-ec2-metadata-token': self.get_imds_auth_token()}

    def is_running_in_ec2(self) -> bool:
        try:
            result = requests.head(f'{EC2_INSTANCE_METADATA_URL_PREFIX}/instance-id', headers=self.get_imds_auth_header(), timeout=1)
            if result.status_code == 200:
                return True
            else:
                return False
        except requests.exceptions.ConnectionError:
            return False
        except Exception as e:
            raise e

    def get_instance_identity_document(self) -> EC2InstanceIdentityDocument:
        response = requests.get(EC2_INSTANCE_IDENTITY_DOCUMENT_URL, headers=self.get_imds_auth_header(), timeout=5)
        if response.status_code != 200:
            raise exceptions.SocaException(
                error_code=errorcodes.EC2_INSTANCE_METADATA_FAILED,
                message=f'failed to retrieve ec2 instance identity document. statuscode: ({response.status_code})'
            )
        return EC2InstanceIdentityDocument(**Utils.from_json(response.text))

    def get_iam_security_credentials(self) -> str:
        response = requests.get(f'{EC2_INSTANCE_METADATA_URL_PREFIX}/iam/security-credentials', headers=self.get_imds_auth_header())
        if response.status_code != 200:
            raise exceptions.SocaException(
                error_code=errorcodes.EC2_INSTANCE_METADATA_FAILED,
                message=f'Failed to retrieve ec2 instance-metadata iam security-credentials. '
                        f'statuscode: ({response.status_code})'
            )
        return response.text.strip()
