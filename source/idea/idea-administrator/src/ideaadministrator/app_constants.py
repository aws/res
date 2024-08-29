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


INSTALLER_CONFIG_DEFAULTS_FILE = 'installer_config_defaults.yml'
INSTALLER_CONFIG_FILE = 'installer_config.yml'
AWS_ENDPOINTS_FILE = 'aws_endpoints.json'

CLUSTER_NAME_PREFIX = 'res-'
CLUSTER_NAME_MIN_MAX_LENGTH = (8, 11)

ACM_CERTIFICATE_SELF_SIGNED_DOMAIN = 'IDEA.DEFAULT.CREATE.YOUR.OWN.CERT'
ACM_CERTIFICATE_SELF_SIGNED_DOMAIN_OLD = 'SOCA.DEFAULT.CREATE.YOUR.OWN.CERT'

LOG_RETENTION_ROLE_NAME = 'log-retention'

DEPLOYMENT_OPTION_INSTALL_IDEA = 'install-idea'
DEPLOYMENT_OPTION_INSTALL_IDEA_USING_EXISTING_RESOURCES = 'install-idea-using-existing-resources'

S3_MOUNT_BUCKET_READ_ONLY_ROLE_NAME = 's3-mount-bucket-read-only'
S3_MOUNT_BUCKET_READ_WRITE_ROLE_NAME = 's3-mount-bucket-read-write'
CUSTOM_CREDENTIAL_BROKER_ROLE_NAME = 'custom-credential-broker-lambda-role'

USER_SESSION_DB_HASH_KEY = 'owner'
USER_SESSION_DB_RANGE_KEY = 'idea_session_id'

DCV_HOST_DB_HASH_KEY = 'instance_id'
DCV_HOST_DB_IDEA_SESSION_ID_KEY = 'idea_session_id'
DCV_HOST_DB_IDEA_SESSION_OWNER_KEY = 'idea_session_owner'

