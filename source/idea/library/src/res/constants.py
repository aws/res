#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

ADMIN_ROLE = "admin"
USER_ROLE = "user"

PROJECT_ROLE_ASSIGNMENT_TYPE = "project"
VALID_ROLE_ASSIGNMENT_RESOURCE_TYPES = [PROJECT_ROLE_ASSIGNMENT_TYPE]
ROLE_ASSIGNMENT_ACTOR_USER_TYPE = "user"
ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE = "group"
VALID_ROLE_ASSIGNMENT_ACTOR_TYPES = [
    ROLE_ASSIGNMENT_ACTOR_USER_TYPE,
    ROLE_ASSIGNMENT_ACTOR_GROUP_TYPE,
]
PROJECT_MEMBER_ROLE_ID = "project_member"
INVALID_ROLE_ASSIGNMENT_RESOURCE_TYPE = "Resource type value is not recognized"

# This regex is defined based on the POSIX username schema (https://systemd.io/USER_NAMES/) and
# SAM-Account-Name schema (https://learn.microsoft.com/en-us/windows/win32/adschema/a-samaccountname).
AD_SAM_ACCOUNT_NAME_MAX_LENGTH = 20
AD_SAM_ACCOUNT_NAME_REGEX = (
    rf"[a-zA-Z0-9_.][a-zA-Z0-9_.-]{{1,{AD_SAM_ACCOUNT_NAME_MAX_LENGTH}}}"
)

CLUSTER_ADMIN_USERNAME = "clusteradmin"
USERNAME_REGEX = rf"^{AD_SAM_ACCOUNT_NAME_REGEX}$"
USERNAME_ERROR_MESSAGE = (
    f"Username (SAM-Account-Name of the AD user) doesn't match the regex pattern {USERNAME_REGEX}. "
    f"Username may only contain lower and upper case ASCII letters, "
    f"digits, period, underscore, and hyphen, with the restriction that "
    f"hyphen is not allowed as first character of the username. "
    f"The maximum length of username is 20."
)
