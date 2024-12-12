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

from sanic_ext import Config

from res.constants import CUSTOM_DOMAIN_NAME_FOR_VDI_KEY, CUSTOM_DOMAIN_NAME_FOR_WEBAPP_KEY
from res.resources.cluster_settings import CLUSTER_SETTINGS_TABLE_NAME
from res.utils import table_utils


def get_cors_config() -> Config:
    allowed_origins = [
        "https://*.amazonaws.com"
    ]
    custom_webapp_domain_name = table_utils.get_item(
        table_name=CLUSTER_SETTINGS_TABLE_NAME,
        key={"key": CUSTOM_DOMAIN_NAME_FOR_WEBAPP_KEY}
    )["value"]
    if custom_webapp_domain_name:
        allowed_origins.append(f"https://*.{custom_webapp_domain_name}")

    custom_vdi_domain_name = table_utils.get_item(
        table_name=CLUSTER_SETTINGS_TABLE_NAME,
        key={"key": CUSTOM_DOMAIN_NAME_FOR_VDI_KEY}
    )["value"]
    if custom_vdi_domain_name:
        allowed_origins.append(f"https://*.{custom_vdi_domain_name}")

    return Config(
        cors_origins=allowed_origins,
        cors_allow_headers=["content-type", "accept",
                            "authorization", "x-xsrf-token", "x-request-id"]
    )
