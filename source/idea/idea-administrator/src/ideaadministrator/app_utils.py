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


class AdministratorUtils:

    @staticmethod
    def get_ec2_username(os_: str) -> str:
        return 'ec2-user'

    @staticmethod
    def get_session_manager_url(aws_partition: str, aws_region: str, instance_id: str) -> str:
        # todo - implement this for other partitions (aws-iso, aws-iso-b)

        # console_prefix - comes before 'console' in the URI - including the '.'
        # console_suffix - comes after 'console' in the URI - including '.'
        console_prefix = ''
        console_suffix = '.aws.amazon.com'

        if aws_partition == 'aws-cn':
            console_prefix = ''
            console_suffix = '.amazonaws.cn'
        elif aws_partition == 'aws-us-gov':
            console_prefix = ''
            console_suffix = '.amazonaws-us-gov.com'
        else:
            console_prefix = f'{aws_region}.'
            console_suffix = '.aws.amazon.com'

        return str(f'https://{console_prefix}console{console_suffix}'
                   f'/systems-manager/session-manager'
                   f'/{instance_id}?region={aws_region}')
