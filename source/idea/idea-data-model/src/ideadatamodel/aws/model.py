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
    'EC2InstanceIdentityDocument',
    'EC2InstanceMonitorEvent',
    'EC2SpotFleetInstance',
    'AutoScalingGroupInstance',
    'ServiceQuota',
    'CheckServiceQuotaResult',
    'EC2InstanceUnitPrice',
    'AwsProjectBudget',
    'SocaAnonymousMetrics',
    'SESSendEmailRequest',
    'SESSendRawEmailRequest',
    'AWSPartition',
    'AWSRegion',
    'EC2PrefixList',
    'EC2PrefixListEntry',
    'CognitoUser',
    'CognitoUserMFAOptions',
    'CognitoUserPoolPasswordPolicy',
    'AWSTag'
)

from ideadatamodel.aws import EC2Instance
from ideadatamodel.common import SocaAmount
from ideadatamodel.model_utils import ModelUtils
from ideadatamodel import SocaBaseModel

from typing import Optional, List, Dict
from troposphere.cloudformation import AWSCustomObject
from datetime import datetime


class EC2InstanceIdentityDocument(SocaBaseModel):
    accountId: Optional[str]
    architecture: Optional[str]
    availabilityZone: Optional[str]
    billingProducts: Optional[str]
    devpayProductCodes: Optional[str]
    marketplaceProductCodes: Optional[str]
    imageId: Optional[str]
    instanceId: Optional[str]
    instanceType: Optional[str]
    kernelId: Optional[str]
    pendingTime: Optional[str]
    privateIp: Optional[str]
    ramdiskId: Optional[str]
    region: Optional[str]
    version: Optional[str]


class EC2InstanceMonitorEvent(SocaBaseModel):
    type: Optional[str]
    instance: Optional[EC2Instance]


class EC2SpotFleetInstance(SocaBaseModel):
    InstanceId: Optional[str]
    InstanceType: Optional[str]
    SpotInstanceRequestId: Optional[str]
    InstanceHealth: Optional[str]


class AutoScalingGroupInstance(SocaBaseModel):
    ProtectedFromScaleIn: Optional[bool]
    AvailabilityZone: Optional[str]
    InstanceId: Optional[str]
    WeightedCapacity: Optional[str]
    HealthStatus: Optional[str]
    LifecycleState: Optional[str]
    InstanceType: Optional[str]


class ServiceQuota(SocaBaseModel):
    quota_name: Optional[str]
    available: Optional[int]
    consumed: Optional[int]
    desired: Optional[int]


class CheckServiceQuotaResult(SocaBaseModel):
    quotas: Optional[List[ServiceQuota]]

    def is_available(self) -> bool:
        if self.quotas is None:
            return False
        for quota in self.quotas:
            consumed = ModelUtils.get_as_int(quota.consumed, 0)
            desired = ModelUtils.get_as_int(quota.desired, 0)
            available = ModelUtils.get_as_int(quota.available, 0)
            if consumed + desired > available:
                return False
        return True

    def find_insufficient_quotas(self) -> List[ServiceQuota]:
        if self.quotas is None:
            return []
        result = []
        for quota in self.quotas:
            available = ModelUtils.get_as_int(quota.available, 0)
            desired = ModelUtils.get_as_int(quota.desired, 0)
            if desired > available:
                result.append(quota)
        return result

    def __bool__(self):
        return self.is_available()


class EC2InstanceUnitPrice(SocaBaseModel):
    reserved: Optional[float]
    ondemand: Optional[float]


class AwsProjectBudget(SocaBaseModel):
    budget_name: Optional[str]
    budget_limit: Optional[SocaAmount]
    actual_spend: Optional[SocaAmount]
    forecasted_spend: Optional[SocaAmount]


class SocaAnonymousMetrics(AWSCustomObject):
    resource_type = "Custom::SendAnonymousMetrics"
    props = {
        "ServiceToken": (str, True),
        "DesiredCapacity": (str, True),
        "InstanceType": (str, True),
        "Efa": (str, True),
        "ScratchSize": (str, True),
        "RootSize": (str, True),
        "SpotPrice": (str, True),
        "BaseOS": (str, True),
        "StackUUID": (str, True),
        "KeepForever": (str, True),
        "TerminateWhenIdle": (str, True),
        "FsxLustre": (str, True),
        "FsxLustreInfo": (dict, True),
        "Dcv": (str, True),
        "Version": (str, True),
        "Misc": (str, True),
        "Region": (str, True)
    }


class SESSendEmailRequest(SocaBaseModel):
    to_addresses: Optional[List[str]]
    cc_addresses: Optional[List[str]]
    bcc_addresses: Optional[List[str]]
    subject: Optional[str]
    body: Optional[str]


class SESSendRawEmailRequest(SocaBaseModel):
    pass


class AWSRegion(SocaBaseModel):
    name: Optional[str]
    region: Optional[str]


class AWSPartition(SocaBaseModel):
    name: Optional[str]
    partition: Optional[str]
    regions: List[AWSRegion]
    dns_suffix: Optional[str]

    def get_region(self, region: str) -> Optional[AWSRegion]:
        for region_ in self.regions:
            if region_.region == region:
                return region_
        return None


class EC2PrefixListEntry(SocaBaseModel):
    cidr: Optional[str]
    description: Optional[str]


class EC2PrefixList(SocaBaseModel):
    prefix_list_id: Optional[str]
    prefix_list_name: Optional[str]
    prefix_list_arn: Optional[str]
    max_entries: Optional[int]
    state: Optional[str]
    entries: Optional[List[EC2PrefixListEntry]]
    address_family: Optional[str]

    @staticmethod
    def from_aws_result(result: Dict) -> 'EC2PrefixList':
        return EC2PrefixList(
            prefix_list_id=ModelUtils.get_value_as_string('PrefixListId', result),
            prefix_list_name=ModelUtils.get_value_as_string('PrefixListName', result),
            prefix_list_arn=ModelUtils.get_value_as_string('PrefixListArn', result),
            state=ModelUtils.get_value_as_string('State', result),
            address_family=ModelUtils.get_value_as_string('AddressFamily', result),
            max_entries=ModelUtils.get_value_as_int('MaxEntries', result),
        )


class CognitoUserMFAOptions(SocaBaseModel):
    DeliveryMedium: Optional[str]
    AttributeName: Optional[str]


class CognitoUser(SocaBaseModel):
    Username: Optional[str]
    UserAttributes: Optional[List[Dict]]
    UserCreateDate: Optional[datetime]
    UserLastModifiedDate: Optional[datetime]
    Enabled: Optional[bool]
    UserStatus: Optional[str]
    MFAOptions: Optional[CognitoUserMFAOptions]
    PreferredMfaSetting: Optional[str]
    UserMFASettingList: Optional[List[str]]

    def get_user_attribute(self, name: str) -> Optional[str]:
        if ModelUtils.is_empty(self.UserAttributes):
            return None
        for attribute in self.UserAttributes:
            attr_name = ModelUtils.get_value_as_string('Name', attribute)
            if attr_name == name:
                return ModelUtils.get_value_as_string('Value', attribute)
        return None

    @property
    def email(self) -> Optional[str]:
        return self.get_user_attribute('email')

    @property
    def uid(self) -> Optional[int]:
        uid = self.get_user_attribute('custom:uid')
        return ModelUtils.get_as_int(uid, None)

    @property
    def gid(self) -> Optional[int]:
        gid = self.get_user_attribute('custom:gid')
        return ModelUtils.get_as_int(gid, None)

class CognitoUserPoolPasswordPolicy(SocaBaseModel):
    minimum_length: Optional[int]
    require_uppercase: Optional[bool]
    require_lowercase: Optional[bool]
    require_numbers: Optional[bool]
    require_symbols: Optional[bool]
    temporary_password_validity_days: Optional[int]


class AWSTag(SocaBaseModel):
    Key: str
    Value: str
