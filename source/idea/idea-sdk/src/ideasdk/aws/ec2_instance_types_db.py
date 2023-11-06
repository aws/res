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

from ideasdk.protocols import SocaContextProtocol
from ideadatamodel import exceptions, errorcodes, EC2InstanceType

from typing import Optional, List, Set
from cacheout import Cache
import botocore
import botocore.exceptions

INSTANCE_TYPES_MAX_SIZE = 1000
INSTANCE_TYPES_TTL_SECS = 15 * 24 * 60 * 60


class EC2InstanceTypesDB:

    def __init__(self, context: SocaContextProtocol):
        self._context = context
        self._logger = context.logger()
        self._cache = Cache(
            maxsize=INSTANCE_TYPES_MAX_SIZE,
            ttl=INSTANCE_TYPES_TTL_SECS
        )
        self._instance_type_names = set(self._instance_type_names_from_botocore())

    def _instance_type_names_from_botocore(self) -> List[str]:
        return self._context.aws().ec2()._service_model.shape_for('InstanceType').enum  # noqa

    def all_instance_type_names(self) -> Set[str]:
        return self._instance_type_names

    def get(self, instance_type: str) -> Optional[EC2InstanceType]:
        cache_key = instance_type
        ec2_instance_type = self._cache.get(key=cache_key)
        if ec2_instance_type is not None:
            return ec2_instance_type

        if instance_type not in self._instance_type_names:
            raise exceptions.SocaException(
                error_code=errorcodes.INVALID_EC2_INSTANCE_TYPE,
                message=f'ec2 instance_type is invalid: {instance_type}'
            )

        try:
            result = self._context.aws().ec2().describe_instance_types(
                InstanceTypes=[instance_type]
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'InvalidInstanceType':
                raise exceptions.SocaException(
                    error_code=errorcodes.INVALID_EC2_INSTANCE_TYPE,
                    message=f'ec2 instance_type is invalid: {instance_type}'
                )
            else:
                raise e

        ec2_instance_type = EC2InstanceType(data=result['InstanceTypes'][0])
        self._cache.set(key=cache_key, value=ec2_instance_type)
        return ec2_instance_type
