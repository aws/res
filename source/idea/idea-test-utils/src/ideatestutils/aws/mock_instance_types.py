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
import jinja2.exceptions

from ideasdk.utils import Jinja2Utils, Utils
from ideadatamodel.aws import EC2InstanceType
from ideadatamodel import exceptions, errorcodes

from typing import List

MOCK_INSTANCE_TYPES = [
    't3.micro',
    'c5.large',
    'c5.xlarge',
    'c5n.18xlarge'
]


class MockInstanceTypes:
    """
    Mock Instance Types to support Unit Tests

    1. applicable instance types json file must be created under the ideatestutils.aws.instance_types package
    2. instance type must be added to allowed_instance_types member list
    """

    def get_instance_type_names(self) -> List[str]:
        return list(MOCK_INSTANCE_TYPES)

    def get_instance_type(self, instance_type: str) -> EC2InstanceType:
        print(f'fetching mock instance type: {instance_type} ...')

        if instance_type not in MOCK_INSTANCE_TYPES:
            raise exceptions.SocaException(
                error_code=errorcodes.INVALID_EC2_INSTANCE_TYPE,
                message=f'ec2 instance_type is invalid: {instance_type}'
            )

        try:
            env = Jinja2Utils.env_using_package_loader(
                package_name='ideatestutils.aws',
                package_path='templates'
            )
            template = env.get_template(f'{instance_type}.json')
        except jinja2.exceptions.TemplateNotFound:
            raise exceptions.SocaException(
                error_code=errorcodes.INVALID_EC2_INSTANCE_TYPE,
                message=f'ec2 instance_type is invalid: {instance_type}'
            )
        content = template.render()
        instance_type_dict = Utils.from_json(content)
        return EC2InstanceType(data=instance_type_dict)
