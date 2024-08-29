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

CONFIG_LEVEL_INFO = 0
CONFIG_LEVEL_WARNING = 1
CONFIG_LEVEL_CRITICAL = 2

DIRECTORYSERVICE_OPENLDAP = 'openldap'
DIRECTORYSERVICE_ACTIVE_DIRECTORY = 'activedirectory'
DIRECTORYSERVICE_AWS_MANAGED_ACTIVE_DIRECTORY = 'aws_managed_activedirectory'
DEFAULT_AUTH_PROVIDER = DIRECTORYSERVICE_OPENLDAP

IDENTITY_PROVIDER_COGNITO_IDP = 'cognito-idp'
IDENTITY_PROVIDER_KEYCLOAK = 'keycloak'

STORAGE_PROVIDER_EFS = 'efs'
STORAGE_PROVIDER_FSX_CACHE = 'fsx_cache'
STORAGE_PROVIDER_FSX_LUSTRE = 'fsx_lustre'
STORAGE_PROVIDER_FSX_NETAPP_ONTAP = 'fsx_netapp_ontap'
STORAGE_PROVIDER_FSX_OPENZFS = 'fsx_openzfs'
STORAGE_PROVIDER_FSX_WINDOWS_FILE_SERVER = 'fsx_windows_file_server'
STORAGE_PROVIDER_S3_BUCKET = 's3_bucket'
DEFAULT_STORAGE_PROVIDER = STORAGE_PROVIDER_EFS
SUPPORTED_STORAGE_PROVIDERS = [
    STORAGE_PROVIDER_EFS,
    STORAGE_PROVIDER_FSX_CACHE,
    STORAGE_PROVIDER_FSX_LUSTRE,
    STORAGE_PROVIDER_FSX_NETAPP_ONTAP,
    STORAGE_PROVIDER_FSX_OPENZFS,
    STORAGE_PROVIDER_FSX_WINDOWS_FILE_SERVER,
    STORAGE_PROVIDER_S3_BUCKET
]

# Volume Type strings
VOLUME_TYPE_GP2 = 'gp2'
VOLUME_TYPE_GP3 = 'gp3'
VOLUME_TYPE_IO1 = 'io1'
VOLUME_TYPE_IO2 = 'io2'
#
#
# EBS volume type defaults
#
DEFAULT_VOLUME_TYPE_SCRATCH = VOLUME_TYPE_IO1
DEFAULT_VOLUME_TYPE_COMPUTE = VOLUME_TYPE_GP3
DEFAULT_VOLUME_TYPE_VDI = VOLUME_TYPE_GP3
#
# EBS volume encryption behavior
#
DEFAULT_VOLUME_ENCRYPTION_VDI = True
DEFAULT_VOLUME_ENCRYPTION_COMPUTE = True

VDI_HOST_POLICY_RESOURCE_TAG = 'vdi-host-policy'
VDI_SECURITY_GROUP_RESOURCE_TAG = 'vdi-security-group'
VDI_RESOURCE_TAG_KEY = 'res:Resource'

# VDI networking options
DEFAULT_VDI_RANDOMIZE_SUBNETS = False
DEFAULT_VDI_SUBNET_AUTORETRY = True


SCHEDULER_OPENPBS = 'openpbs'

QUEUE_MODE_FIFO = 'fifo'
QUEUE_MODE_FAIRSHARE = 'fairshare'
QUEUE_MODES = [QUEUE_MODE_FIFO, QUEUE_MODE_FAIRSHARE]
DEFAULT_QUEUE_MODE = QUEUE_MODE_FIFO

SCALING_MODE_SINGLE_JOB = 'single-job'
SCALING_MODE_MULTIPLE_JOBS = 'batch'
DEFAULT_SCALING_MODE = SCALING_MODE_SINGLE_JOB

ALLOWED_BASEOS = ['rhel8', 'rhel9', 'amazonlinux2']

TOPIC_BROADCAST = 'idea.app.broadcast'
MESSAGE_RELOAD = 'app.reload'

TOPIC_EC2_INSTANCE_MONITOR_EVENTS = 'idea.aws.ec2.instance-monitor'
EC2_INSTANCE_MONITOR_EVENT_CACHE_REFRESH = 'instance-cache-refreshed'
EC2_INSTANCE_MONITOR_EVENT_INSTANCE_STATE_RUNNING = 'instance-state.running'

TOPIC_NODE_MONITOR_EVENTS = 'idea.scheduler.node-monitor'
TOPIC_JOB_MONITOR_EVENTS = 'idea.scheduler.job-monitor'

LOGGER_TEMPLATE_APP = 'app'
LOGGER_TEMPLATE_ROOT = 'root'
DEFAULT_LOGGER_NAME = 'idea'

AWS_TAG_CFN_LOGICAL_ID = 'aws:cloudformation:logical-id'
AWS_TAG_CFN_STACK_NAME = 'aws:cloudformation:stack-name'
AWS_TAG_CFN_STACK_ID = 'aws:cloudformation:stack-id'
AWS_TAG_EC2SPOT_FLEET_REQUEST_ID = 'aws:ec2spot:fleet-request-id'
AWS_TAG_AUTOSCALING_GROUP_NAME = 'aws:autoscaling:groupName'

IDEA_TAG_PREFIX = 'res:'

IDEA_TAG_NODE_TYPE =  IDEA_TAG_PREFIX + 'NodeType'

IDEA_TAG_ENVIRONMENT_NAME =  IDEA_TAG_PREFIX + 'EnvironmentName'
IDEA_TAG_MODULE_ID =  IDEA_TAG_PREFIX + 'ModuleId'
IDEA_TAG_MODULE_NAME =  IDEA_TAG_PREFIX + 'ModuleName'
IDEA_TAG_MODULE_VERSION =  IDEA_TAG_PREFIX + 'ModuleVersion'
IDEA_TAG_PROJECT =  IDEA_TAG_PREFIX + 'Project'
IDEA_TAG_AMI_BUILDER =  IDEA_TAG_PREFIX + 'AmiBuilder'

BI_TAG_PREFIX = 'bi:'

BI_TAG_DEPLOYMENT =  BI_TAG_PREFIX + 'Deployment'

IDEA_TAG_NAME = 'Name'

IDEA_TAG_JOB_ID =  IDEA_TAG_PREFIX + 'JobId'
IDEA_TAG_JOB_GROUP =  IDEA_TAG_PREFIX + 'JobGroup'
IDEA_TAG_JOB_NAME =  IDEA_TAG_PREFIX + 'JobName'
IDEA_TAG_JOB_OWNER =  IDEA_TAG_PREFIX + 'JobOwner'
IDEA_TAG_JOB_QUEUE =  IDEA_TAG_PREFIX + 'JobQueue'
IDEA_TAG_KEEP_FOREVER =  IDEA_TAG_PREFIX + 'KeepForever'
IDEA_TAG_TERMINATE_WHEN_IDLE =  IDEA_TAG_PREFIX + 'TerminateWhenIdle'
IDEA_TAG_QUEUE_TYPE =  IDEA_TAG_PREFIX + 'QueueType'
IDEA_TAG_SCALING_MODE =  IDEA_TAG_PREFIX + 'ScalingMode'
IDEA_TAG_CAPACITY_TYPE =  IDEA_TAG_PREFIX + 'CapacityType'
IDEA_TAG_FSX =  IDEA_TAG_PREFIX + 'FSx'
IDEA_TAG_COMPUTE_STACK =  IDEA_TAG_PREFIX + 'StackId'
IDEA_TAG_CREATED_FROM =  IDEA_TAG_PREFIX + 'CreatedFrom'
IDEA_TAG_CREATED_ON =  IDEA_TAG_PREFIX + 'CreatedOn'
IDEA_TAG_BACKUP_PLAN =  IDEA_TAG_PREFIX + 'BackupPlan'
IDEA_TAG_STACK_TYPE =  IDEA_TAG_PREFIX + 'StackType'
IDEA_TAG_IDEA_SESSION_ID =  IDEA_TAG_PREFIX + 'IDEASessionUUID'
IDEA_TAG_DCV_SESSION_ID =  IDEA_TAG_PREFIX + 'DCVSessionUUID'

NODE_TYPE_COMPUTE = 'compute-node'
NODE_TYPE_DCV_HOST = 'virtual-desktop-dcv-host'
NODE_TYPE_APP = 'app'
NODE_TYPE_INFRA = 'infra'
NODE_TYPE_AMI_BUILDER = 'ami-builder'
NODE_TYPE_UNKNOWN = 'unknown'

STACK_TYPE_BOOTSTRAP = 'bootstrap'
STACK_TYPE_CLUSTER = 'cluster'
STACK_TYPE_APP = 'app'
STACK_TYPE_ALB = 'alb'
STACK_TYPE_JOB = 'job'
STACK_TYPE_DEBUG = 'debug'

SPOT_PRICE_AUTO = 'auto'

EC2_SERVICE_QUOTA_ONDEMAND = 1
EC2_SERVICE_QUOTA_SPOT = 2
EC2_SERVICE_QUOTA_DEDICATED = 3
EC2_SERVICE_CPU_OPTIONS_UNSUPPORTED_FAMILY = ('t2', 'hpc6a', 'a1')

JOB_PARAM_NODES = 'nodes'
JOB_PARAM_CPUS = 'cpus'
JOB_PARAM_MEMORY = 'memory'
JOB_PARAM_GPUS = 'gpus'
JOB_PARAM_MPIPROCS = 'mpiprocs'
JOB_PARAM_BASE_OS = 'base_os'
JOB_PARAM_INSTANCE_AMI = 'instance_ami'
JOB_PARAM_INSTANCE_TYPES = 'instance_types'
JOB_PARAM_FORCE_RESERVED_INSTANCES = 'force_reserved_instances'
JOB_PARAM_SPOT = 'spot'
JOB_PARAM_SPOT_PRICE = 'spot_price'
JOB_PARAM_SPOT_ALLOCATION_COUNT = 'spot_allocation_count'
JOB_PARAM_SPOT_ALLOCATION_STRATEGY = 'spot_allocation_strategy'
JOB_PARAM_SUBNET_IDS = 'subnet_ids'
JOB_PARAM_SECURITY_GROUPS = 'security_groups'
JOB_PARAM_INSTANCE_PROFILE = 'instance_profile'
JOB_PARAM_KEEP_EBS_VOLUMES = 'keep_ebs_volumes'
JOB_PARAM_ENABLE_SCRATCH = 'enable_scratch'
JOB_PARAM_ROOT_STORAGE_SIZE = 'root_storage_size'
JOB_PARAM_SCRATCH_STORAGE_SIZE = 'scratch_storage_size'
JOB_PARAM_SCRATCH_IOPS = 'scratch_storage_iops'
JOB_PARAM_FSX_LUSTRE = 'fsx_lustre'
JOB_PARAM_FSX_LUSTRE_S3_BACKEND = 'fsx_lustre_s3_backend'
JOB_PARAM_FSX_LUSTRE_EXISTING_FSX = 'fsx_lustre_existing_fsx'
JOB_PARAM_FSX_LUSTRE_IMPORT_PATH = 'fsx_lustre_import_path'
JOB_PARAM_FSX_LUSTRE_EXPORT_PATH = 'fsx_lustre_export_path'
JOB_PARAM_FSX_LUSTRE_DEPLOYMENT_TYPE = 'fsx_lustre_deployment_type'
JOB_PARAM_FSX_LUSTRE_PER_UNIT_THROUGHPUT = 'fsx_lustre_per_unit_throughput'
JOB_PARAM_FSX_LUSTRE_SIZE = 'fsx_lustre_size'
JOB_PARAM_ENABLE_INSTANCE_STORE = 'enable_instance_store'
JOB_PARAM_ENABLE_EFA_SUPPORT = 'enable_efa_support'
JOB_PARAM_ENABLE_HT_SUPPORT = 'enable_ht_support'
JOB_PARAM_ENABLE_PLACEMENT_GROUP = 'enable_placement_group'
JOB_PARAM_ENALE_SYSTEM_METRICS = 'enable_system_metrics'
JOB_PARAM_ENABLE_ANONYMOUS_METRICS = 'enable_anonymous_metrics'
JOB_PARAM_LICENSES = 'licenses'
JOB_PARAM_WALLTIME = 'walltime'
JOB_PARAM_COMPUTE_STACK = 'compute_stack'
JOB_PARAM_STACK_ID = 'stack_id'
JOB_PARAM_JOB_GROUP = 'job_group'
JOB_PARAM_JOB_STARTED_EMAIL_TEMPLATE = 'job_started_email_template'
JOB_PARAM_JOB_COMPLETED_EMAIL_TEMPLATE = 'job_completed_email_template'
JOB_PARAM_CUSTOM_PARAMS = 'custom_params'
JOB_OPTION_TERMINATE_WHEN_IDLE = 'terminate_when_idle'
JOB_OPTION_KEEP_FOREVER = 'keep_forever'
JOB_OPTION_TAGS = 'tags'

MAX_SECURITY_GROUPS = 4

DEFAULT_NODES = 1
DEFAULT_CPUS = 1
DEFAULT_FORCE_RESERVED_INSTANCES = False
DEFAULT_KEEP_EBS_VOLUMES = False
DEFAULT_ROOT_STORAGE_SIZE = 10
DEFAULT_SCRATCH_STORAGE_SIZE = 0
DEFAULT_SCRATCH_IOPS = 0

DEFAULT_FSX_LUSTRE_PER_UNIT_THROUGHPUT = 200
DEFAULT_FSX_LUSTRE_SIZE_GB = 1200

FSX_LUSTRE_DEPLOYMENT_TYPE_PERSISTENT_1 = 'persistent_1'
FSX_LUSTRE_DEPLOYMENT_TYPE_PERSISTENT_2 = 'persistent_2'
FSX_LUSTRE_DEPLOYMENT_TYPE_SCRATCH_1 = 'scratch_1'
FSX_LUSTRE_DEPLOYMENT_TYPE_SCRATCH_2 = 'scratch_2'
DEFAULT_FSX_LUSTRE_DEPLOYMENT_TYPE = FSX_LUSTRE_DEPLOYMENT_TYPE_SCRATCH_2
FSX_LUSTRE_PER_UNIT_THROUGHPUT_TYPES = (FSX_LUSTRE_DEPLOYMENT_TYPE_PERSISTENT_1, FSX_LUSTRE_DEPLOYMENT_TYPE_PERSISTENT_2)

DEFAULT_ENABLE_EFA_SUPPORT = False
DEFAULT_ENABLE_HT_SUPPORT = False
DEFAULT_ENABLE_PLACEMENT_GROUP = False
DEFAULT_SPOT_ALLOCATION_STRATEGY = 'capacity-optimized'
DEFAULT_ENABLE_SYSTEM_METRICS = False
DEFAULT_ENABLE_SPOT = False
DEFAULT_ENABLE_SCRATCH = False
DEFAULT_TERMINATE_WHEN_IDLE = 0
DEFAULT_KEEP_FOREVER = False

EC2_PLACEMENT_GROUP_STRATEGY_CLUSTER = 'cluster'

SECONDS_IN_MINUTE = 60
SECONDS_IN_HOUR = 60 * SECONDS_IN_MINUTE

SELECT_CHOICE_OTHER = 'other'

# Supported OS
OS_AMAZONLINUX2 = 'amazonlinux2'
OS_RHEL8 = 'rhel8'
OS_RHEL9 = 'rhel9'
OS_UBUNTU2204 = 'ubuntu2204'
OS_WINDOWS = 'windows'
SUPPORTED_OS = (OS_AMAZONLINUX2, OS_RHEL8, OS_RHEL9, OS_WINDOWS, OS_UBUNTU2204)
SUPPORTED_LINUX_OS = (OS_AMAZONLINUX2, OS_RHEL8, OS_RHEL9, OS_UBUNTU2204)

# Platforms
PLATFORM_LINUX = 'linux'
PLATFORM_WINDOWS = 'windows'

CLICK_SETTINGS = dict(
    help_option_names=['-h', '--help'],
    max_content_width=1200)

AWS_SOLUTION_ID = 'SO0280'
DEFAULT_ENCODING = 'utf-8'
DEFAULT_LOCALE = 'en_US'
DEFAULT_TIMEZONE = 'America/Los_Angeles'

# modules
MODULE_BOOTSTRAP = 'bootstrap'
MODULE_GLOBAL_SETTINGS = 'global-settings'
MODULE_CLUSTER = 'cluster'
MODULE_IDENTITY_PROVIDER = 'identity-provider'
MODULE_DIRECTORYSERVICE = 'directoryservice'
MODULE_SHARED_STORAGE = 'shared-storage'
MODULE_SCHEDULER = 'scheduler'
MODULE_CLUSTER_MANAGER = 'cluster-manager'
MODULE_VIRTUAL_DESKTOP_CONTROLLER = 'virtual-desktop-controller'
MODULE_BASTION_HOST = 'bastion-host'
ALL_MODULES = [
    MODULE_BOOTSTRAP,
    MODULE_GLOBAL_SETTINGS,
    MODULE_CLUSTER,
    MODULE_IDENTITY_PROVIDER,
    MODULE_DIRECTORYSERVICE,
    MODULE_SHARED_STORAGE,
    MODULE_SCHEDULER,
    MODULE_CLUSTER_MANAGER,
    MODULE_VIRTUAL_DESKTOP_CONTROLLER,
    MODULE_BASTION_HOST
]

# module types
MODULE_TYPE_APP = 'app'
MODULE_TYPE_CONFIG = 'config'
MODULE_TYPE_STACK = 'stack'

# group types
GROUP_TYPE_USER = 'user'
GROUP_TYPE_PROJECT = 'project'
GROUP_TYPE_MODULE = 'module'
GROUP_TYPE_CLUSTER = 'cluster'
ALL_GROUP_TYPES = [
    GROUP_TYPE_USER,
    GROUP_TYPE_PROJECT,
    GROUP_TYPE_MODULE,
    GROUP_TYPE_CLUSTER
]
GROUP_TYPE_EXTERNAL = "external"
GROUP_TYPE_INTERNAL = "internal"


ADMIN_ROLE = 'admin'
USER_ROLE = 'user'

# project defaults
DEFAULT_PROJECT = 'default'

DEFAULT_COPYRIGHT_TEXT = 'Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.'

# metrics
METRICS_PROVIDER_CLOUDWATCH = 'cloudwatch'
METRICS_PROVIDER_PROMETHEUS = 'prometheus'
METRICS_PROVIDER_AMAZON_MANAGED_PROMETHEUS = 'amazon_managed_prometheus'

# services
SERVICE_ID_LEADER_ELECTION = 'leader-election'
SERVICE_ID_DISTRIBUTED_LOCK = 'distributed-lock'
SERVICE_ID_METRICS = 'metrics-service'

# idea service account
IDEA_SERVICE_ACCOUNT = 'ideaserviceaccount'

# open api spec version
OPEN_API_SPEC_VERSION = '3.0.1'

#
# Caveat definitions
#
CAVEATS = dict()
#
# SSM service discovery namespace is not available
#
CAVEATS['SSM_DISCOVERY_RESTRICTED_REGION_LIST'] = [
    'af-south-1',
    'ap-northeast-3',
    'eu-south-1',
    'me-central-1',
    'me-south-1',
    'us-gov-east-1',
    'us-gov-west-1'
    ]
CAVEATS['SSM_DISCOVERY_FALLBACK_REGION'] = 'us-east-1'


#
# Kinesis streams does not support StreamData in CloudFormation
#
CAVEATS['KINESIS_STREAMS_CLOUDFORMATION_UNSUPPORTED_STREAMMODEDETAILS_REGION_LIST'] = [
    'us-gov-east-1',
    'us-gov-west-1'
]

#
# Route53 cross-zone Alias records are not permitted
# (creates CNAME records instead)
#
CAVEATS['ROUTE53_CROSS_ZONE_ALIAS_RESTRICTED_REGION_LIST'] = [
    'us-gov-east-1',
    'us-gov-west-1'
]

#
# FIPS endpoint is default
#
CAVEATS['COGNITO_REQUIRE_FIPS_ENDPOINT_REGION_LIST'] = [
    'us-gov-east-1',
    'us-gov-west-1'
]

#
# Cognito Advanced Security is not available
#
CAVEATS['COGNITO_ADVANCED_SECURITY_UNAVAIL_REGION_LIST'] = [
    'us-gov-east-1',
    'us-gov-west-1'
]

#
# No SQS FIFO queues
#
CAVEATS['SQS_NO_FIFO_SUPPORT_REGION_LIST'] = [
    'us-gov-east-1',
    'us-gov-west-1'
]

#
# No SNS FIFO queues
#
CAVEATS['SNS_NO_FIFO_SUPPORT_REGION_LIST'] = [
    'us-gov-east-1',
    'us-gov-west-1'
]

# module set
DEFAULT_MODULE_SET = 'default'

# api invocation source
API_INVOCATION_SOURCE_UNIX_SOCKET = 'unix-socket'
API_INVOCATION_SOURCE_HTTP = 'http'

# SSO
SSO_IDP_PROVIDER_OIDC = 'OIDC'
SSO_IDP_PROVIDER_SAML = 'SAML'
SSO_SOURCE_PROVIDER_NAME_REGEX = "^(?!^Cognito$)[\\w._:/-]{1,128}$"
SSO_SOURCE_PROVIDER_NAME_ERROR_MESSAGE = "Only use word character or a single character in the list [\".\", \"_\", \":\", \"/\", \"-\"] for SSO source provider name. " +\
    "Must be between 1 and 128 characters long." +\
    "SourceProviderName may not be Cognito"

SCRIPT_LOCATION_ERROR_MESSAGE = 'Script location is incorrect. Script must be https://, s3://, or file://'

SECURITY_GROUP_ERROR_MESSAGE = 'Security group is not valid'

POLICY_ARN_ERROR_MESSAGE = 'Policy is not valid'

# API Validation Regex and ErrorMessages
FILE_SYSTEM_NAME_REGEX = "^[a-z0-9_]{3,18}$"
FILE_SYSTEM_NAME_ERROR_MESSAGE = "Only use lowercase alphabets, numbers and underscore (_) for file system name. " +\
            "Must be between 3 and 18 characters long."

FILE_SYSTEM_TITLE_REGEX = "^[a-zA-Z0-9\s_-]{3,48}$"
FILE_SYSTEM_TITLE_ERROR_MESSAGE = "Only use valid alphanumeric, hyphens (-), underscores (_), and spaces ( ) characters for the file system title. " +\
            "Must be between 3 and 48 characters long."

FILE_SYSTEM_TITLE_KEY = "title"
FILE_SYSTEM_PROVIDER_KEY = "provider"
FILE_SYSTEM_PROJECTS_KEY = "projects"
FILE_SYSTEM_ALLOWED_KEYS_TO_UPDATE = [FILE_SYSTEM_TITLE_KEY, FILE_SYSTEM_PROJECTS_KEY]
FILE_SYSTEM_VALID_FILTER_KEYS = [FILE_SYSTEM_TITLE_KEY, FILE_SYSTEM_PROVIDER_KEY, FILE_SYSTEM_PROJECTS_KEY]

FILE_SYSTEM_FILTER_KEY_REGEX = f"^({'|'.join(FILE_SYSTEM_VALID_FILTER_KEYS)})$"
FILE_SYSTEM_FILTER_KEY_ERROR_MESSAGE = "Only use valid filter keys for file systems."

FILE_SYSTEM_FILTER_TITLE_REGEX = "^[a-zA-Z0-9\s_-]*$"
FILE_SYSTEM_FILTER_TITLE_ERROR_MESSAGE = "Only use valid alphanumeric, hyphens (-), underscores (_), and spaces ( ) characters for the file system title."

FILE_SYSTEM_FILTER_PROVIDERS_REGEX = f"^({'|'.join([STORAGE_PROVIDER_EFS, STORAGE_PROVIDER_FSX_LUSTRE, STORAGE_PROVIDER_FSX_NETAPP_ONTAP, STORAGE_PROVIDER_S3_BUCKET])})$"
FILE_SYSTEM_FILTER_PROVIDERS_ERROR_MESSAGE = "Only use supported storage providers."

MOUNT_DIRECTORY_REGEX = "^/[a-z0-9-]{3,18}$"
MOUNT_DIRECTORY_ERROR_MESSAGE = "Only use lowercase alphabets, numbers, " +\
    "and hyphens (-) for mount directory. Must be between 3 and 18 characters long."

S3_BUCKET_ARN_REGEX = "^(?:arn:(?:aws(?:-cn|-us-gov)?)):s3:::([a-z0-9][a-z0-9-.]{1,61}[a-z0-9])(?:/[a-z0-9-.]+)*/?$"
S3_BUCKET_ARN_ERROR_MESSAGE = "The provided ARN does not adhere to the required format for an Amazon S3 bucket ARN. A properly formatted bucket ARN should follow the pattern 'arn:aws:s3:::bucket-name', where 'bucket-name' is the name of the S3 bucket."

S3_BUCKET_ARN_PREFIX_REGEX = "^arn:aws(?:-cn|-us-gov)?:s3:::[^/]+/(.*)"

IAM_ROLE_ARN_REGEX = "^(?:arn:(?:aws(?:-cn|-us-gov)?)):iam::\\d{12}:role/[/a-zA-Z0-9+=,.@_-]{0,511}[a-zA-Z0-9+=,.@_-]{1,64}$"
IAM_ROLE_ARN_ERROR_MESSAGE = "The provided ARN does not adhere to the required format for an IAM role ARN. A properly formatted IAM role ARN should follow the pattern 'arn:aws:iam::account-id:role/optional-path-prefix/role-name', where 'account-id' is your AWS account ID and 'role-name' is the name of the IAM role."

IAM_ROLE_NAME_CAPTURE_GROUP_REGEX = "^(?:arn:(?:aws(?:-cn|-us-gov)?)):iam::\\d{12}:role/(?:[a-zA-Z0-9+=,.@_-]+/)*([a-zA-Z0-9+=,.@_-]+)$"

IAM_ROLE_NAME_REGEX = "^[a-zA-Z0-9+=,.@_-]{1,64}$"
IAM_ROLE_NAME_ERROR_MESSAGE = "The provided IAM role name does not adhere to the required format. IAM role names can contain alphanumeric characters and the following special characters: +=,.@_- They must be between 1 and 64 characters long."

MOUNT_DRIVE_REGEX = "^[ABD-Z]{1}$"
MOUNT_DRIVE_ERROR_MESSAGE = "Only use an uppercase alphabet for mount drive"
ONTAP_STORAGE_CAPACITY_RANGE = (1024, 196608)

PROJECT_ID_REGEX = "^[a-z0-9-_.]{3,40}$"
PROJECT_ID_ERROR_MESSAGE = "Only use lowercase alphabets, numbers, hyphens (-), underscores (_), or periods (.) for project id. " +\
    "Must be between 3 and 40 characters long."

SOFTWARE_STACK_NAME_REGEX = SESSION_NAME_REGEX = "^.{3,50}$"
SOFTWARE_STACK_NAME_ERROR_MESSAGE = SESSION_NAME_ERROR_MESSAGE = "Use any characters " +\
    "and form a name of length between 3 and 50 characters, inclusive for software stack name."

INVALID_RANGE_ERROR_MESSAGE = "Input out of permitted range"

VALID_ROLE_ASSIGNMENT_RESOURCE_TYPES = ["project"]
VALID_ROLE_ASSIGNMENT_ACTOR_TYPES = ["user","group"]
PROJECT_MEMBER_ROLE_ID = "project_member"
PROJECT_OWNER_ROLE_ID = "project_owner"
PROJECT_MEMBER_ROLE_NAME = "Project Member"
PROJECT_OWNER_ROLE_NAME = "Project Owner"
VALID_ROLE_ASSIGNMENT_ROLE_NAMES = [PROJECT_MEMBER_ROLE_NAME, PROJECT_OWNER_ROLE_NAME]
INVALID_ROLE_ASSIGNMENT_RESOURCE_TYPE = "Resource type value is not recognized"
INVALID_ROLE_ASSIGNMENT_ACTOR_TYPE = "Actor type value is not recognized"
INVALID_ROLE_ASSIGNMENT_ROLE_ID = "Role ID value is not recognized"
INVALID_ROLE_ASSIGNMENT_ROLE_NAME = "Role name value is not recognized"

ROLE_ASSIGNMENT_RESOURCE_ID_REGEX = "^[a-z0-9-_]{3,36}$"
ROLE_ASSIGNMENT_RESOURCE_ID_ERROR_MESSAGE = "Resource ID contains invalid characters"

ROLE_ASSIGNMENT_RESOURCE_KEY_REGEX = f"^[a-z0-9-_]{{3,36}}:({'|'.join(VALID_ROLE_ASSIGNMENT_RESOURCE_TYPES)})$"
ROLE_ASSIGNMENT_RESOURCE_KEY_ERROR_MESSAGE = "Resource key format was wrong, or contained invalid characters"

# This regex is defined based on the POSIX username schema (https://systemd.io/USER_NAMES/) and
# SAM-Account-Name schema (https://learn.microsoft.com/en-us/windows/win32/adschema/a-samaccountname).
AD_SAM_ACCOUNT_NAME_MAX_LENGTH = 20
AD_SAM_ACCOUNT_NAME_REGEX = rf'[a-zA-Z0-9_.][a-zA-Z0-9_.-]{{1,{AD_SAM_ACCOUNT_NAME_MAX_LENGTH}}}'

# The total allowable number of characters for group name is 65.
GROUP_NAME_REGEX = rf'[a-zA-Z0-9_. -]{{1,65}}'

USERNAME_REGEX = rf'^{AD_SAM_ACCOUNT_NAME_REGEX}$'
USERNAME_ERROR_MESSAGE = (f"Username (SAM-Account-Name of the AD user) doesn't match the regex pattern {USERNAME_REGEX}. "
                          f"Username may only contain lower and upper case ASCII letters, "
                          f"digits, period, underscore, and hyphen, with the restriction that "
                          f"hyphen is not allowed as first character of the username. "
                          f"The maximum length of username is 20.")

ROLE_ASSIGNMENT_ACTOR_ID_REGEX = rf'^({AD_SAM_ACCOUNT_NAME_REGEX}|{GROUP_NAME_REGEX})$'
ROLE_ASSIGNMENT_ACTOR_ID_ERROR_MESSAGE = f"Actor ID doesn't match the regex pattern {ROLE_ASSIGNMENT_ACTOR_ID_REGEX}"

ROLE_ASSIGNMENT_ACTOR_KEY_REGEX = rf"^({AD_SAM_ACCOUNT_NAME_REGEX}:user|{GROUP_NAME_REGEX}:group)$"
ROLE_ASSIGNMENT_ACTOR_KEY_ERROR_MESSAGE = f"Actor key doesn't match the regex pattern {ROLE_ASSIGNMENT_ACTOR_KEY_REGEX}"

S3_BUCKET_IAM_ROLE_RESOURCE_TAG_KEY = "res:Resource"
S3_BUCKET_IAM_ROLE_RESOURCE_TAG_VALUE = "s3-bucket-iam-role"

S3_BUCKET_IAM_ROLE_ERROR_MESSAGE = "The provided role either does not exist or lacks proper tagging for RES."

API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_STAGE = "prod"
API_GATEWAY_CUSTOM_CREDENTIAL_BROKER_RESOURCE = "ObjectStorageTempCredentials"

OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX = "PROJECT_NAME_PREFIX"
OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX = "PROJECT_NAME_AND_USERNAME_PREFIX"
OBJECT_STORAGE_NO_CUSTOM_PREFIX = "NO_CUSTOM_PREFIX"

ROLE_ID_REGEX = "^[a-z0-9_]{3,36}$"
ROLE_ID_ERROR_MESSAGE = "Only use lowercase alphabets, numbers, or underscores (_) for role id. " +\
    "Must be between 3 and 36 characters long."

ROLE_NAME_REGEX = "^[a-zA-Z0-9-_ ]{3,36}$"
ROLE_NAME_ERROR_MESSAGE = "Only use alphabets, numbers, spaces, dashes (-), or underscores (_) for role name. " +\
    "Must be between 3 and 36 characters long."

ROLE_DESC_REGEX = "^[a-zA-Z0-9-_ ]{0,50}$"
ROLE_DESC_ERROR_MESSAGE = "Only use alphabets, numbers, spaces, dashes (-), or underscores (_) for role description. " +\
    "Can be up to 50 characters long."

# Since role assignment objects are small in size (~300 bytes) and we want to conserve DDB RCUs, we query/get role assignments based on number of groups
# https://stackoverflow.com/questions/73452943/what-count-as-one-read-in-dynamodb
CONSERVE_DDB_RCU_LIST_GROUP_ROLES = 3
