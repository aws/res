#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

RESOURCE_DIR = Path(os.path.realpath(__file__)).parent.parent.parent.parent
TEMPLATES_DIR = os.path.join(RESOURCE_DIR, "config", "templates")
BASE_PERMISSION_PROFILE_CONFIG_PATH = os.path.join(
    RESOURCE_DIR, "config", "base-permission-profile-config.yaml"
)
BASE_SOFTWARE_STACK_CONFIG_PATH = os.path.join(
    RESOURCE_DIR, "config", "base-software-stack-config.yaml"
)
REGIONAL_TIMEZONE_CONFIG = os.path.join(
    RESOURCE_DIR, "config", "region_timezone_config.yml"
)
DEFAULT_EMAIL_TEMPLATES_CONFIG_PATH = os.path.join(
    RESOURCE_DIR, "config", "email_templates.yml"
)
REGIONAL_AMI_CONFIG = os.path.join(RESOURCE_DIR, "config", "region_ami_config.yml")
REGION_ELB_ACCOUNT_ID_CONFIG = os.path.join(
    RESOURCE_DIR, "config", "region_elb_account_id.yml"
)
