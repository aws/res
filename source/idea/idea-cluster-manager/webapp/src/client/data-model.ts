/* tslint:disable */
/* eslint-disable */
/* This file is generated using IDEA invoke typings task. */
/* Do not modify this file manually. */
/**
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the License). You may not use this file except in compliance
 * with the License. A copy of the License is located at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 * OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 * and limitations under the License.
 */

export type SocaUserInputParamType =
    | "text"
    | "password"
    | "new-password"
    | "path"
    | "confirm"
    | "select"
    | "raw_select"
    | "checkbox"
    | "autocomplete"
    | "select_or_text"
    | "choices"
    | "auto"
    | "image_upload"
    | "heading1"
    | "heading2"
    | "heading3"
    | "heading4"
    | "heading5"
    | "heading6"
    | "paragraph"
    | "code"
    | "datepicker"
    | "radio-group"
    | "file-upload"
    | "tiles"
    | "container"
    | "expandable"
    | "attribute_editor";
export type VirtualDesktopBaseOS = "amazonlinux2" | "rhel8" | "rhel9" | "windows";
export type SocaMemoryUnit = "bytes" | "kib" | "mib" | "gib" | "tib" | "kb" | "mb" | "gb" | "tb";
export type VirtualDesktopArchitecture = "x86_64" | "arm64";
export type VirtualDesktopGPU = "NO_GPU" | "NVIDIA" | "AMD";
export type SocaSortOrder = "asc" | "desc";
export type SocaQueueMode = "fifo" | "fairshare" | "license-optimized";
export type SocaScalingMode = "single-job" | "batch";
export type SocaSpotAllocationStrategy = "capacity-optimized" | "lowest-price" | "diversified";
export type SocaJobState = "transition" | "queued" | "held" | "waiting" | "running" | "exit" | "subjob_expired" | "subjob_begun" | "moved" | "finished" | "suspended";
export type SocaCapacityType = "on-demand" | "spot" | "mixed";
export type VirtualDesktopSessionType = "CONSOLE" | "VIRTUAL";
export type VirtualDesktopSessionState = "PROVISIONING" | "CREATING" | "INITIALIZING" | "READY" | "RESUMING" | "STOPPING" | "STOPPED" | "ERROR" | "DELETING" | "DELETED";
export type DayOfWeek = "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday";
export type VirtualDesktopScheduleType = "WORKING_HOURS" | "STOP_ALL_DAY" | "START_ALL_DAY" | "CUSTOM_SCHEDULE" | "NO_SCHEDULE";
export type VirtualDesktopSessionPermissionActorType = "USER" | "GROUP";
export type DryRunOption = "true" | "json:job" | "json:bom" | "json:budget" | "json:quota" | "json:queue" | "notification:email" | "debug";
export type SocaComputeNodeState = "busy" | "down" | "free" | "offline" | "job-busy" | "job-exclusive" | "provisioning" | "resv-exclusive" | "stale" | "stale-unknown" | "unresolvable" | "wait-provisioning" | "initializing";
export type SocaComputeNodeSharing = "default-excl" | "default-exlchost" | "default-shared" | "force-excl" | "force-exclhost" | "ignore-excl";
export type SocaJobPlacementArrangement = "free" | "pack" | "scatter" | "vscatter";
export type SocaJobPlacementSharing = "excl" | "shared" | "exclhost" | "vscatter";
export type SnapshotStatus = "IN_PROGRESS" | "COMPLETED" | "FAILED";
export type ApplySnapshotStatus = "IN_PROGRESS" | "COMPLETED" | "FAILED" | "ROLLBACK_IN_PROGRESS" | "ROLLBACK_COMPLETE" | "ROLLBACK_FAILED";

export interface FileList {
    cwd?: string;
    files?: FileData[];
}
export interface FileData {
    owner?: string;
    group?: string;
    file_id?: string;
    name?: string;
    ext?: string;
    is_dir?: boolean;
    is_hidden?: boolean;
    is_sym_link?: boolean;
    is_encrypted?: boolean;
    size?: number;
    mod_date?: string;
    children_count?: number;
    color?: string;
    icon?: string;
    folder_chain_icon?: string;
    thumbnail_url?: string;
}
export interface RemoveAdminUserResult {
    user?: User;
}
export interface User {
    username?: string;
    password?: string;
    email?: string;
    uid?: number;
    gid?: number;
    group_name?: string;
    additional_groups?: string[];
    login_shell?: string;
    home_dir?: string;
    sudo?: boolean;
    status?: string;
    enabled?: boolean;
    password_last_set?: string;
    password_max_age?: number;
    created_on?: string;
    updated_on?: string;
    synced_on?: string;
    role?: string;
    is_active?: string;
}

export interface Snapshot {
    s3_bucket_name?: string;
    snapshot_path?: string;
    status?: SnapshotStatus;
    created_on?: string;
    failure_reason?: string
}

export interface ListSnapshotsRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
}

export interface ListSnapshotsResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: Snapshot[];
    filters?: SocaFilter[];
}

export interface ApplySnapshot {
    s3_bucket_name?: string;
    snapshot_path?: string;
    status?: ApplySnapshotStatus;
    created_on?: string;
    failure_reason?: string
}

export interface ListApplySnapshotRecordsRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
}

export interface ListApplySnapshotRecordsResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: Snapshot[];
    filters?: SocaFilter[];
}

export interface CreateFileResult {}
export interface DisableGroupResult {}
export interface DeleteHpcLicenseResourceRequest {
    name?: string;
}
export interface GetModuleMetadataResult {
    module?: SocaUserInputModuleMetadata;
}
export interface SocaUserInputModuleMetadata {
    name?: string;
    title?: string;
    description?: string;
    sections?: SocaUserInputSectionMetadata[];
    markdown?: string;
}
export interface SocaUserInputSectionMetadata {
    name?: string;
    module?: string;
    title?: string;
    description?: string;
    required?: boolean;
    review?: SocaUserInputSectionReview;
    params?: SocaUserInputParamMetadata[];
    groups?: SocaUserInputGroupMetadata[];
    markdown?: string;
}
export interface SocaUserInputSectionReview {
    prompt?: string;
}
export interface SocaUserInputParamMetadata {
    name?: string;
    template?: string;
    optional?: boolean;
    title?: string;
    prompt?: boolean;
    description?: React.ReactNode;
    description2?: string;
    help_text?: string;
    help_url?: string;
    param_type?: SocaUserInputParamType;
    data_type?: string;
    custom_type?: string;
    multiple?: boolean;
    multiline?: boolean;
    auto_enter?: boolean;
    auto_focus?: boolean;
    unique?: boolean;
    default?: unknown;
    readonly?: boolean;
    validate?: SocaUserInputValidate;
    choices?: SocaUserInputChoice[];
    choices_meta?: {
        [k: string]: unknown;
    };
    dynamic_choices?: boolean;
    choices_empty_label?: string;
    refreshable?: boolean;
    ignore_case?: boolean;
    match_middle?: boolean;
    tag?: string;
    export?: boolean;
    when?: SocaUserInputParamCondition;
    expose?: SocaUserInputParamExposeOptions;
    markdown?: string;
    developer_notes?: string;
    custom?: {
        [k: string]: unknown;
    };
    container_items?: SocaUserInputParamMetadata[];
    custom_error_message?: string;
    container_group_name?: string;
    attributes_editor_type?: string;
}
export interface SocaUserInputValidate {
    eq?: unknown;
    not_eq?: unknown;
    in?: string | unknown[];
    not_in?: string | unknown[];
    gt?: unknown;
    gte?: unknown;
    lt?: unknown;
    lte?: unknown;
    min?: unknown;
    max?: unknown;
    range?: SocaUserInputRange;
    not_in_range?: SocaUserInputRange;
    regex?: string;
    not_regex?: string;
    exact?: string;
    starts_with?: string;
    ends_with?: string;
    empty?: boolean;
    not_empty?: boolean;
    contains?: unknown;
    not_contains?: unknown;
    required?: boolean;
    auto_prefix?: string;
    message?: string;
}
export interface SocaUserInputRange {
    type?: string;
    from?: unknown[];
    to?: unknown[];
}
export interface SocaUserInputChoice {
    title?: string;
    value?: unknown;
    disabled?: boolean;
    checked?: boolean;
    options?: SocaUserInputChoice[];
    description?: string;
}
export interface SocaUserInputParamCondition {
    eq?: unknown;
    not_eq?: unknown;
    in?: string | unknown[];
    not_in?: string | unknown[];
    gt?: unknown;
    gte?: unknown;
    lt?: unknown;
    lte?: unknown;
    min?: unknown;
    max?: unknown;
    range?: SocaUserInputRange;
    not_in_range?: SocaUserInputRange;
    regex?: string;
    not_regex?: string;
    exact?: string;
    starts_with?: string;
    ends_with?: string;
    empty?: boolean;
    not_empty?: boolean;
    contains?: unknown;
    not_contains?: unknown;
    param?: string;
    and?: SocaUserInputParamCondition[];
    or?: SocaUserInputParamCondition[];
}
export interface SocaUserInputParamExposeOptions {
    cli?: SocaInputParamCliOptions;
    web_app?: boolean;
}
export interface SocaInputParamCliOptions {
    long_name?: string;
    short_name?: string;
    required?: string;
    help_text?: string;
}
export interface SocaUserInputGroupMetadata {
    name?: string;
    module?: string;
    section?: string;
    title?: string;
    description?: string;
    params?: SocaUserInputParamMetadata[];
}
export interface CreateGroupRequest {
    group?: Group;
}
export interface Group {
    title?: string;
    description?: string;
    name?: string;
    ds_name?: string;
    gid?: number;
    group_type?: string;
    ref?: string;
    enabled?: boolean;
    created_on?: string;
    updated_on?: string;
    synced_on?: string;
    role?: string;
    type?: string;
}
export interface SocaJobEstimatedBudgetUsage {
    budget_name?: string;
    budget_limit?: SocaAmount;
    actual_spend?: SocaAmount;
    forecasted_spend?: SocaAmount;
    job_usage_percent?: number;
    job_usage_percent_with_savings?: number;
}
export interface SocaAmount {
    amount: number;
    unit?: string;
}
export interface DeleteQueueProfileResult {}
export interface GetHpcApplicationResult {
    application?: HpcApplication;
}
export interface HpcApplication {
    application_id?: string;
    title?: string;
    description?: string;
    thumbnail_url?: string;
    thumbnail_data?: string;
    form_template?: SocaUserInputModuleMetadata;
    job_script_interpreter?: string;
    job_script_type?: string;
    job_script_template?: string;
    projects?: Project[];
    created_on?: string;
    updated_on?: string;
}
export interface Project {
    project_id?: string;
    name?: string;
    title?: string;
    description?: string;
    enabled?: boolean;
    ldap_groups?: string[];
    users?: string[];
    enable_budgets?: boolean;
    budget?: AwsProjectBudget;
    tags?: SocaKeyValue[];
    created_on?: string;
    updated_on?: string;
    scripts?: Scripts;
    policy_arns?: string[];
    security_groups?: string[];
}

export interface Scripts {
    windows?: ScriptEvents;
    linux?: ScriptEvents;
}

export interface ScriptEvents {
    on_vdi_start?: Script[];
    on_vdi_configured?: Script[];
}

export interface Script {
    script_location?: string;
    arguments?: string[];
}

export interface SecurityGroup {
    group_id?: string;
    group_name?: string;
}

export interface Policy {
    policy_arn?: string;
    policy_name?: string;
}

export interface FileSystemsNotOnboarded {
    [filesystemId: string]: EFSFileSystem | FSxONTAPFileSystem;
}

export interface FileSystem {
    name?: string;
    storage?: any;
}

export interface EFSFileSystem {
    efs?: any;
}

export interface FSxONTAPSVM {
    storage_virtual_machine?: any;
}

export interface FSxONTAPVolume {
    volume?: any;
}

export interface FSxONTAPFileSystem {
    filesystem?: any;
    svm?: FSxONTAPSVM[];
    volume: FSxONTAPVolume[];
}

export interface FSxLUSTREFileSystem {
    filesystem?: any;
}

export interface S3Bucket {
    name: string
    storage: {
        title: string;
        provider: string;
        scope: string[];
        projects?: string[];
        mount_dir: string;
        s3_bucket: {
            bucket_arn: string;
            read_only: boolean;
            custom_bucket_prefix?: string;
            iam_role_arn?: string;
        }
    }
}

export interface AwsProjectBudget {
    budget_name?: string;
    budget_limit?: SocaAmount;
    actual_spend?: SocaAmount;
    forecasted_spend?: SocaAmount;
}
export interface SocaKeyValue {
    key?: string;
    value?: string;
}
export interface DeleteUserRequest {
    username?: string;
}
export interface GetSessionConnectionInfoRequest {
    connection_info?: VirtualDesktopSessionConnectionInfo;
}
export interface VirtualDesktopSessionConnectionInfo {
    dcv_session_id?: string;
    idea_session_id?: string;
    idea_session_owner?: string;
    endpoint?: string;
    username?: string;
    web_url_path?: string;
    access_token?: string;
    failure_reason?: string;
}
export interface CreateSoftwareStackResponse {
    software_stack?: VirtualDesktopSoftwareStack;
}
export interface VirtualDesktopSoftwareStack {
    stack_id?: string;
    base_os?: VirtualDesktopBaseOS;
    name?: string;
    description?: string;
    created_on?: string;
    updated_on?: string;
    ami_id?: string;
    failure_reason?: string;
    enabled?: boolean;
    min_storage?: SocaMemory;
    min_ram?: SocaMemory;
    architecture?: VirtualDesktopArchitecture;
    gpu?: VirtualDesktopGPU;
    projects?: Project[];
}
export interface SocaMemory {
    value: number;
    unit: SocaMemoryUnit;
}
export interface ListFilesRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    cwd?: string;
}
export interface SocaPaginator {
    total?: number;
    page_size?: number;
    start?: number;
    cursor?: string;
}
export interface SocaSortBy {
    key?: string;
    order?: SocaSortOrder;
}
export interface SocaDateRange {
    key?: string;
    start?: string;
    end?: string;
}
export interface SocaBaseModel {}
export interface SocaFilter {
    key?: string;
    value?: unknown;
    eq?: unknown;
    in?: string | unknown[];
    like?: string;
    starts_with?: string;
    ends_with?: string;
    and?: SocaFilter[];
    or?: SocaFilter[];
}
export interface GetInstanceTypeOptionsResult {
    instance_types?: SocaInstanceTypeOptions[];
}
export interface SocaInstanceTypeOptions {
    name?: string;
    weighted_capacity?: number;
    cpu_options_supported?: boolean;
    default_core_count?: number;
    default_vcpu_count?: number;
    default_threads_per_core?: number;
    threads_per_core?: number;
    memory?: SocaMemory;
    ebs_optimized?: boolean;
}
export interface ResetPasswordResult {}
export interface HpcQueueProfile {
    queue_profile_id?: string;
    title?: string;
    description?: string;
    name?: string;
    projects?: Project[];
    queues?: string[];
    enabled?: boolean;
    queue_mode?: SocaQueueMode;
    scaling_mode?: SocaScalingMode;
    terminate_when_idle?: number;
    keep_forever?: boolean;
    stack_uuid?: string;
    queue_management_params?: SocaQueueManagementParams;
    default_job_params?: SocaJobParams;
    created_on?: string;
    updated_on?: string;
    status?: string;
    limit_info?: LimitCheckResult;
    queue_size?: number;
}
export interface SocaQueueManagementParams {
    max_running_jobs?: number;
    max_provisioned_instances?: number;
    max_provisioned_capacity?: number;
    wait_on_any_job_with_license?: boolean;
    allowed_instance_types?: string[];
    excluded_instance_types?: string[];
    restricted_parameters?: string[];
    allowed_security_groups?: string[];
    allowed_instance_profiles?: string[];
}
export interface SocaJobParams {
    nodes?: number;
    cpus?: number;
    memory?: SocaMemory;
    gpus?: number;
    mpiprocs?: number;
    walltime?: string;
    base_os?: string;
    instance_ami?: string;
    instance_types?: string[];
    force_reserved_instances?: boolean;
    spot?: boolean;
    spot_price?: SocaAmount;
    spot_allocation_count?: number;
    spot_allocation_strategy?: SocaSpotAllocationStrategy;
    subnet_ids?: string[];
    security_groups?: string[];
    instance_profile?: string;
    keep_ebs_volumes?: boolean;
    root_storage_size?: SocaMemory;
    enable_scratch?: boolean;
    scratch_provider?: string;
    scratch_storage_size?: SocaMemory;
    scratch_storage_iops?: number;
    fsx_lustre?: SocaFSxLustreConfig;
    enable_instance_store?: boolean;
    enable_efa_support?: boolean;
    enable_ht_support?: boolean;
    enable_placement_group?: boolean;
    enable_system_metrics?: boolean;
    enable_anonymous_metrics?: boolean;
    licenses?: SocaJobLicenseAsk[];
    compute_stack?: string;
    stack_id?: string;
    job_group?: string;
    job_started_email_template?: string;
    job_completed_email_template?: string;
    custom_params?: {
        [k: string]: string;
    };
}
export interface SocaFSxLustreConfig {
    enabled?: boolean;
    existing_fsx?: string;
    s3_backend?: string;
    import_path?: string;
    export_path?: string;
    deployment_type?: string;
    per_unit_throughput?: number;
    size?: SocaMemory;
}
export interface SocaJobLicenseAsk {
    name?: string;
    count?: number;
}
export interface LimitCheckResult {
    success?: boolean;
    limit_type?: string;
    queue_threshold?: number;
    queue_current?: number;
    group_threshold?: number;
    group_current?: number;
}
export interface ListPermissionProfilesRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
}
export interface ProvisionAlwaysOnNodesResult {
    stack_name?: string;
    stack_id?: string;
}
export interface JobGroupMetrics {
    total?: JobMetrics;
    jobs?: {
        [k: string]: JobMetrics;
    };
}
export interface JobMetrics {
    active_jobs?: number;
    desired_capacity?: number;
}
export interface RemoveUserFromGroupResult {
    group?: Group;
}
export interface CreateProjectRequest {
    project?: Project;
}
export interface PutRoleAssignmentRequest {
    request_id: string;
    resource_id: string;
    actor_id: string;
    resource_type: string;
    actor_type: string;
    role_id: string;
}
export interface PutRoleAssignmentSuccessResponse {
    request_id: string;
    status_code: string;
}
export interface PutRoleAssignmentErrorResponse {
    request_id: string;
    error_code: string;
    message?: string;
}
export interface BatchPutRoleAssignmentRequest {
    items?: PutRoleAssignmentRequest[];
}
export interface BatchPutRoleAssignmentResponse {
    items?: PutRoleAssignmentSuccessResponse[];
    errors?: PutRoleAssignmentErrorResponse[];
}

export interface DeleteRoleAssignmentRequest {
    request_id: string;
    resource_id: string;
    actor_id: string;
    resource_type: string;
    actor_type: string;
}
export interface DeleteRoleAssignmentSuccessResponse {
    request_id: string;
    status_code: string;
}
export interface DeleteRoleAssignmentErrorResponse {
    request_id: string;
    error_code: string;
    message?: string;
}
export interface BatchDeleteRoleAssignmentRequest {
    items?: DeleteRoleAssignmentRequest[];
}
export interface BatchDeleteRoleAssignmentResponse {
    items?: DeleteRoleAssignmentSuccessResponse[];
    errors?: DeleteRoleAssignmentErrorResponse[];
}
export interface ListRoleAssignmentsRequest {
    paginator?: SocaPaginator;
    resource_key?: string;
    actor_key?: string;
    max_results?: number;
}
export interface RoleAssignment {
    resource_key: string;
    actor_key: string;
    resource_id: string;
    actor_id: string;
    resource_type: string;
    actor_type: string;
    role_id: string;
}
export interface ListRoleAssignmentsResponse {
    items: RoleAssignment[];
}
export interface ProjectPermissions {
  update_personnel: boolean;
  update_status: boolean;
};
export interface VDIPermissions {
  create_terminate_others_sessions: boolean;
  create_sessions: boolean;
}
export interface Role {
    role_id: string;
    name: string;
    description: string;
    projects: ProjectPermissions;
    vdis?: VDIPermissions;
    created_on: string | undefined;
    updated_on: string | undefined;
}
export interface ListRolesRequest {
    paginator?: SocaPaginator;
    include_permissions?: boolean;
}
export interface ListRolesResponse {
    paginator?: SocaPaginator;
    items: Role[];
}
export interface GetRoleRequest {
    role_id?: string;
}
export interface GetRoleResponse {
    role: Role;
}
export interface CreateRoleRequest {
    role: Role;
}
export interface CreateRoleResponse {
  role: Role;
}
export interface DeleteRoleRequest {
  role_id?: string;
}
export interface DeleteRoleResponse {}
export interface UpdateRoleRequest {
  role: Role;
}
export interface UpdateRoleResponse {
  role: Role;
}
export interface CreateFileSystemRequest {
    filesystem?: FileSystem;
}
export interface GetSoftwareStackInfoResponse {
    software_stack?: VirtualDesktopSoftwareStack;
}
export interface AuthResult {
    access_token?: string;
    id_token?: string;
    refresh_token?: string;
    expires_in?: number;
    token_type?: string;
}
export interface GetBasePermissionsRequest {}
export interface DescribeSessionsResponse {
    response?: {
        [k: string]: unknown;
    };
}
export interface UpdateEmailTemplateResult {
    template?: EmailTemplate;
}
export interface EmailTemplate {
    name?: string;
    title?: string;
    template_type?: string;
    subject?: string;
    body?: string;
    created_on?: string;
    updated_on?: string;
}
export interface GetBasePermissionsResponse {
    permissions?: VirtualDesktopPermission[];
}
export interface VirtualDesktopPermission {
    key?: string;
    name?: string;
    description?: string;
    enabled?: boolean;
}
export interface ListJobsRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    queue_type?: string;
    queue?: string;
    states?: SocaJobState[];
}
export interface InitiateAuthRequest {
    client_id?: string;
    auth_flow?: string;
    cognito_username?: string;
    password?: string;
    refresh_token?: string;
    authorization_code?: string;
}
export interface ModuleInfo {
    module_name?: string;
    module_version?: string;
    module_id?: string;
}
export interface SocaInputParamValidationEntry {
    name?: string;
    section?: string;
    message?: string;
    meta?: SocaUserInputParamMetadata;
}
export interface ListAllowedInstanceTypesRequest {
    hibernation_support?: boolean;
    software_stack?: VirtualDesktopSoftwareStack;
}
export interface AuthenticateUserRequest {
    username?: string;
    password?: string;
}
export interface ListHpcApplicationsResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: HpcApplication[];
    filters?: SocaFilter[];
}
export interface ListProjectsResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: Project[];
    filters?: SocaFilter[];
}
export interface ListOnboardedFileSystemsResult {
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: FileSystem[];
    filters?: SocaFilter[];
}
export interface ServiceQuota {
    quota_name?: string;
    available?: number;
    consumed?: number;
    desired?: number;
}
export interface GetGroupRequest {
    group_name?: string;
}
export interface DeleteHpcLicenseResourceResult {}
export interface CreateQueuesRequest {
    queue_profile_id?: string;
    queue_profile_name?: string;
    queue_names?: string;
}
export interface DeleteUserResult {}
export interface GetUserApplicationsRequest {
    username?: string;
    application_ids?: string[];
}
export interface CreateGroupResult {
    group?: Group;
}
export interface HpcLicenseResource {
    name?: string;
    title?: string;
    availability_check_cmd?: string;
    availability_check_status?: string;
    reserved_count?: number;
    available_count?: number;
    created_on?: string;
    updated_on?: string;
}
export interface SocaJob {
    cluster_name?: string;
    cluster_version?: string;
    job_id?: string;
    job_uid?: string;
    job_group?: string;
    project?: string;
    name?: string;
    queue?: string;
    queue_type?: string;
    scaling_mode?: SocaScalingMode;
    owner?: string;
    state?: SocaJobState;
    exit_status?: string;
    provisioned?: boolean;
    error_message?: string;
    queue_time?: string;
    provisioning_time?: string;
    start_time?: string;
    end_time?: string;
    total_time_secs?: number;
    comment?: string;
    debug?: boolean;
    capacity_added?: boolean;
    params?: SocaJobParams;
    provisioning_options?: SocaJobProvisioningOptions;
    estimated_budget_usage?: SocaJobEstimatedBudgetUsage;
    estimated_bom_cost?: SocaJobEstimatedBOMCost;
    execution_hosts?: SocaJobExecutionHost[];
    notifications?: SocaJobNotifications;
}
/**
 * These are job provisioning parameters, that satisfy any of these cases:
 *
 * > computed dynamically based on JobParams provided by the user
 * > are not defined as resources in the scheduler
 * > are primarily used while provisioning capacity for the job
 * > values from soca-configuration in AWS Secrets
 *
 * If any of these values can be potentially be submitted by the user during job submission,
 * these values must be pulled up to JobParams.
 */
export interface SocaJobProvisioningOptions {
    keep_forever?: boolean;
    terminate_when_idle?: number;
    ebs_optimized?: boolean;
    spot_fleet_iam_role_arn?: string;
    compute_fleet_instance_profile_arn?: string;
    apps_fs_dns?: string;
    apps_fs_provider?: string;
    data_fs_dns?: string;
    data_fs_provider?: string;
    es_endpoint?: string;
    stack_uuid?: string;
    s3_bucket?: string;
    s3_bucket_install_folder?: string;
    scheduler_private_dns?: string;
    scheduler_tcp_port?: number;
    ssh_key_pair?: string;
    auth_provider?: string;
    tags?: {
        [k: string]: string;
    };
    anonymous_metrics_lambda_arn?: string;
    instance_types?: SocaInstanceTypeOptions[];
}
export interface SocaJobEstimatedBOMCost {
    line_items?: SocaJobEstimatedBOMCostLineItem[];
    line_items_total?: SocaAmount;
    savings?: SocaJobEstimatedBOMCostLineItem[];
    savings_total?: SocaAmount;
    total?: SocaAmount;
}
export interface SocaJobEstimatedBOMCostLineItem {
    title?: string;
    service?: string;
    product?: string;
    quantity?: number;
    unit?: string;
    unit_price?: SocaAmount;
    total_price?: SocaAmount;
}
export interface SocaJobExecutionHost {
    host?: string;
    instance_id?: string;
    instance_type?: string;
    capacity_type?: SocaCapacityType;
    tenancy?: string;
    reservation?: string;
    execution?: SocaJobExecution;
}
export interface SocaJobExecution {
    run_count?: number;
    runs?: SocaJobExecutionRun[];
}
export interface SocaJobExecutionRun {
    run_id?: string;
    start?: string;
    end?: string;
    exit_code?: number;
    status?: string;
    resources_used?: SocaJobExecutionResourcesUsed;
}
export interface SocaJobExecutionResourcesUsed {
    cpu_time_secs?: number;
    memory?: SocaMemory;
    virtual_memory?: SocaMemory;
    cpus?: number;
    gpus?: number;
    cpu_percent?: number;
}
export interface SocaJobNotifications {
    started?: boolean;
    completed?: boolean;
    subjobs?: boolean;
    job_started_email_template?: string;
    job_completed_email_template?: string;
}
export interface ListFilesResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: FileData[];
    filters?: SocaFilter[];
    cwd?: string;
}
export interface DeleteSessionRequest {
    sessions?: VirtualDesktopSession[];
}
export interface VirtualDesktopSession {
    dcv_session_id?: string;
    idea_session_id?: string;
    base_os?: VirtualDesktopBaseOS;
    name?: string;
    owner?: string;
    type?: VirtualDesktopSessionType;
    server?: VirtualDesktopServer;
    created_on?: string;
    updated_on?: string;
    state?: VirtualDesktopSessionState;
    description?: string;
    software_stack?: VirtualDesktopSoftwareStack;
    project?: Project;
    schedule?: VirtualDesktopWeekSchedule;
    connection_count?: number;
    force?: boolean;
    hibernation_enabled?: boolean;
    is_launched_by_admin?: boolean;
    locked?: boolean;
    failure_reason?: string;
    tags?: Record<string,string>[]
}
export interface VirtualDesktopServer {
    server_id?: string;
    idea_sesssion_id?: string;
    idea_session_owner?: string;
    instance_id?: string;
    instance_type?: string;
    private_ip?: string;
    private_dns_name?: string;
    public_ip?: string;
    public_dns_name?: string;
    availability?: string;
    unavailability_reason?: string;
    console_session_count?: number;
    virtual_session_count?: number;
    max_concurrent_sessions_per_user?: number;
    max_virtual_sessions?: number;
    state?: string;
    locked?: boolean;
    root_volume_size?: SocaMemory;
    root_volume_iops?: number;
    instance_profile_arn?: string;
    security_groups?: string[];
    subnet_id?: string;
    key_pair_name?: string;
}
export interface VirtualDesktopWeekSchedule {
    monday?: VirtualDesktopSchedule;
    tuesday?: VirtualDesktopSchedule;
    wednesday?: VirtualDesktopSchedule;
    thursday?: VirtualDesktopSchedule;
    friday?: VirtualDesktopSchedule;
    saturday?: VirtualDesktopSchedule;
    sunday?: VirtualDesktopSchedule;
}
export interface VirtualDesktopSchedule {
    schedule_id?: string;
    idea_session_id?: string;
    idea_session_owner?: string;
    day_of_week?: DayOfWeek;
    start_up_time?: string;
    shut_down_time?: string;
    schedule_type?: VirtualDesktopScheduleType;
}
export interface UpdateHpcApplicationRequest {
    application?: HpcApplication;
}
export interface SubmitJobRequest {
    job_owner?: string;
    project?: string;
    dry_run?: boolean;
    job_script_interpreter?: string;
    job_script?: string;
}
export interface ConfirmForgotPasswordRequest {
    client_id?: string;
    username?: string;
    confirmation_code?: string;
    password?: string;
}
export interface GetSessionConnectionInfoResponse {
    connection_info?: VirtualDesktopSessionConnectionInfo;
}
export interface UpdateSoftwareStackRequest {
    software_stack?: VirtualDesktopSoftwareStack;
}
export interface DeleteSoftwareStackRequest {
    software_stack?: VirtualDesktopSoftwareStack;
}
export interface DeleteEmailTemplateRequest {
    name?: string;
}
export interface GetModuleInfoRequest {}
export interface DecodedToken {}
export interface ListScheduleTypesRequest {}
export interface UpdateSessionPermissionRequest {
    create?: VirtualDesktopSessionPermission[];
    delete?: VirtualDesktopSessionPermission[];
    update?: VirtualDesktopSessionPermission[];
}
export interface VirtualDesktopSessionPermission {
    idea_session_id?: string;
    idea_session_owner?: string;
    idea_session_name?: string;
    idea_session_instance_type?: string;
    idea_session_state?: VirtualDesktopSessionState;
    idea_session_base_os?: VirtualDesktopBaseOS;
    idea_session_created_on?: string;
    idea_session_hibernation_enabled?: boolean;
    idea_session_type?: VirtualDesktopSessionType;
    permission_profile?: VirtualDesktopPermissionProfile;
    actor_type?: VirtualDesktopSessionPermissionActorType;
    actor_name?: string;
    created_on?: string;
    updated_on?: string;
    expiry_date?: string;
    failure_reason?: string;
}
export interface VirtualDesktopPermissionProfile {
    profile_id?: string;
    title?: string;
    description?: string;
    permissions?: VirtualDesktopPermission[];
    created_on?: string;
    updated_on?: string;
}
export interface UpdateSessionResponse {
    session?: VirtualDesktopSession;
}
export interface ProvisioningQueueMetrics {
    total?: JobMetrics;
    groups?: {
        [k: string]: JobGroupMetrics;
    };
}
export interface CreateProjectResult {
    project?: Project;
}
export interface CreateFileSystemResult {
    filesystem?: FileSystem;
}
export interface SocaInputParamValidationResult {
    entries?: SocaInputParamValidationEntry[];
}
export interface SendNotificationResult {}
export interface GetParamChoicesRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    module?: string;
    param?: string;
    refresh?: boolean;
}
export interface InitiateAuthResult {
    challenge_name?: string;
    session?: string;
    challenge_params?: {
        [k: string]: unknown;
    };
    auth?: AuthResult;
    db_username?: string;
    role?: string;
}
export interface AuthenticateUserResult {
    status?: boolean;
}
export interface ListAllowedInstanceTypesResponse {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing: unknown[];
    filters?: SocaFilter[];
}
export interface EnableProjectRequest {
    project_name?: string;
    project_id?: string;
}
export interface ListPermissionProfilesResponse {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: VirtualDesktopPermissionProfile[];
    filters?: SocaFilter[];
}
export interface ListHpcLicenseResourcesRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
}
export interface GetUserApplicationsResult {
    applications: HpcApplication[];
}
export interface ListClusterModulesRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
}
export interface CreateQueuesResult {}
export interface EnableUserRequest {
    username?: string;
}
export interface GetGroupResult {
    group?: Group;
}
export interface TailFileResult {
    file?: string;
    next_token?: string;
    lines?: string[];
    line_count?: number;
}
export interface GetQueueProfileRequest {
    queue_profile_name?: string;
    queue_profile_id?: string;
    queue_name?: string;
}
export interface DeleteEmailTemplateResult {}
export interface UpdateHpcApplicationResult {
    application?: HpcApplication;
}
export interface ConfirmForgotPasswordResult {}
export interface ListSessionsResponse {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: VirtualDesktopSession[];
    filters?: SocaFilter[];
}
export interface ModifyGroupRequest {
    group?: Group;
}
export interface SubmitJobResult {
    dry_run?: DryRunOption;
    accepted?: boolean;
    job?: SocaJob;
    validations?: JobValidationResult;
    incidentals?: JobValidationResult;
    service_quotas?: ServiceQuota[];
    reserved_instances_unavailable?: boolean;
    service_quota_unavailable?: boolean;
    estimated_bom_cost?: SocaJobEstimatedBOMCost;
    budget_usage?: SocaJobEstimatedBudgetUsage;
}
export interface JobValidationResult {
    results?: JobValidationResultEntry[];
}
export interface JobValidationResultEntry {
    error_code?: string;
    message?: string;
}
export interface GetSessionScreenshotRequest {
    screenshots?: VirtualDesktopSessionScreenshot[];
}
export interface VirtualDesktopSessionScreenshot {
    image_type?: string;
    image_data?: string;
    dcv_session_id?: string;
    idea_session_id?: string;
    idea_session_owner?: string;
    create_time?: string;
    failure_reason?: string;
}
export interface UpdateSoftwareStackResponse {
    software_stack?: VirtualDesktopSoftwareStack;
}
export interface DeleteSoftwareStackResponse {}
export interface GetProjectRequest {
    project_name?: string;
    project_id?: string;
}
export interface GetFileSystemRequest {
    filesystem_name?: string;
    filesystem_id?: string;
}
export interface GetModuleInfoResult {
    module?: ModuleInfo;
}
export interface ListJobsResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: SocaJob[];
    filters?: SocaFilter[];
}
export interface UpdateSessionPermissionResponse {
    permissions?: VirtualDesktopSessionPermission[];
}
export interface SocaUserInputCondition {
    eq?: unknown;
    not_eq?: unknown;
    in?: string | unknown[];
    not_in?: string | unknown[];
    gt?: unknown;
    gte?: unknown;
    lt?: unknown;
    lte?: unknown;
    min?: unknown;
    max?: unknown;
    range?: SocaUserInputRange;
    not_in_range?: SocaUserInputRange;
    regex?: string;
    not_regex?: string;
    exact?: string;
    starts_with?: string;
    ends_with?: string;
    empty?: boolean;
    not_empty?: boolean;
    contains?: unknown;
    not_contains?: unknown;
}
export interface RespondToAuthChallengeRequest {
    client_id?: string;
    session?: string;
    challenge_name?: string;
    challenge_params?: {
        [k: string]: unknown;
    };
    username?: string;
    new_password?: string;
}
export interface GetUserPrivateKeyRequest {
    key_format?: string;
    platform?: string;
}
export interface SocaSchedulerInfo {
    name?: string;
    version?: string;
}
export interface ListClusterModulesResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: unknown[];
    filters?: SocaFilter[];
}
export interface EnableProjectResult {}
export interface ListAllowedInstanceTypesForSessionRequest {
    session?: VirtualDesktopSession;
}
export interface CreateHpcLicenseResourceRequest {
    license_resource?: HpcLicenseResource;
    dry_run?: boolean;
}
export interface SaveFileRequest {
    file?: string;
    content?: string;
}
export interface GetQueueProfileResult {
    queue_profile?: HpcQueueProfile;
}
export interface DeleteQueuesRequest {
    queue_profile_id?: string;
    queue_profile_name?: string;
    queue_names?: string;
}
export interface EnableUserResult {
    user?: User;
}
export interface SocaQueue {
    name?: string;
    enabled?: boolean;
    started?: boolean;
    total_jobs?: number;
    stats?: SocaQueueStats;
}
export interface SocaQueueStats {
    transit?: number;
    queued?: number;
    held?: number;
    waiting?: number;
    running?: number;
    exiting?: number;
    begun?: number;
}
export interface CreateUserRequest {
    user?: User;
    email_verified?: boolean;
}

export interface CreateSnapshotRequest {
    snapshot?: Snapshot;
}

export interface CreateSnapshotResult {
    result?: string;
}

export interface ApplySnapshotRequest {
    snapshot?: Snapshot
}

export interface ApplySnapshotResult {
    message?: string
}

export interface SendNotificationRequest {
    notification?: Notification;
}
export interface Notification {
    username?: string;
    template_name?: string;
    params?: {
        [k: string]: unknown;
    };
    subject?: string;
    body?: string;
}
export interface DeleteHpcApplicationRequest {
    application_id?: string;
}
export interface GetParamChoicesResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: SocaUserInputChoice[];
    filters?: SocaFilter[];
}
export interface SignOutRequest {
    refresh_token?: string;
    sso_auth?: boolean;
}
export interface JobUpdate {
    queue?: string;
    owner?: string;
    job_id?: string;
    timestamp?: string;
}
export interface DeleteJobRequest {
    job_id?: string;
}
export interface GetPermissionProfileRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    profile_id?: string;
}
export interface ModifyGroupResult {
    group?: Group;
}
export interface GetProjectResult {
    project?: Project;
}
export interface GetFileSystemResult {
    filesystem?: FileSystem;
}
export interface ListHpcLicenseResourcesResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: HpcLicenseResource[];
    filters?: SocaFilter[];
}
export interface GetModuleSettingsRequest {
    module_id?: string;
}
// UpdateModuleSettingsRequest types to only allow specific combinations of settings with modules
export enum UpdateModuleSettingsValuesDCVSession {
    IDLE_TIMEOUT = "idle_timeout",
    IDLE_TIMEOUT_WARNING = "idle_timeout_warning",
    CPU_UTILIZATION_THRESHOLD = "cpu_utilization_threshold",
    ALLOWED_SESSIONS_PER_USER = "allowed_sessions_per_user",
    MAX_ROOT_VOLUME_MEMORY = "max_root_volume_memory",
    ALLOWED_INSTANCE_TYPES = "instance_types.allow",
}

export type UpdateModuleSettingsVDC = {
    dcv_session: {
        [key in UpdateModuleSettingsValuesDCVSession]?: unknown;
    };
};
export type UpdateModuleSettingsRequestVDC = {
    module_id: "vdc";
    settings: UpdateModuleSettingsVDC;
};

export enum UpdateModuleSettingsValuesWebPortal {
    TITLE = "title",
    SUBTITLE = "subtitle",
    COPYRIGHT_TEXT = "copyright_text",
}
export type UpdateModuleSettingsWebPortal = {
    web_portal: {
        [key in UpdateModuleSettingsValuesWebPortal]?: unknown;
    };
};
export type UpdateModuleSettingsRequestWebPortal = {
    module_id: "cluster-manager";
    settings: UpdateModuleSettingsWebPortal;
};
export type UpdateModuleSettingsRequest = {
    module_id: string;
    settings?: UpdateModuleSettingsVDC | UpdateModuleSettingsWebPortal;
};
export interface CreateQueueProfileRequest {
    queue_profile?: HpcQueueProfile;
}
export interface GetUserPrivateKeyResult {
    name?: string;
    key_material?: string;
}
export interface SaveFileResult {}
export interface UpdateQueueProfileRequest {
    queue_profile?: HpcQueueProfile;
}
export interface DisableProjectRequest {
    project_name?: string;
    project_id?: string;
}
export interface SocaUserInputHandlers {
    class?: string;
    choices?: string;
    default?: string;
    validate?: string;
    autocomplete?: string;
    filter?: string;
}
export interface ListPermissionsRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    idea_session_id?: string;
    username?: string;
}
export interface ListScheduleTypesResponse {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: string[];
    filters?: SocaFilter[];
}
export interface RespondToAuthChallengeResult {
    challenge_name?: string;
    session?: string;
    challenge_params?: {
        [k: string]: unknown;
    };
    auth?: AuthResult;
}
export interface GetSessionInfoRequest {
    session?: VirtualDesktopSession;
}
export interface ListEmailTemplatesRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
}
export interface ReadFileResult {
    file?: string;
    content_type?: string;
    content?: string;
}
export interface SetParamRequest {
    module?: string;
    param?: string;
    value?: unknown;
}
export interface DeleteQueuesResult {}
export interface ListGroupsRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    username?: string;
}
export interface DisableUserRequest {
    username?: string;
}
export interface CreateHpcLicenseResourceResult {
    license_resource?: HpcLicenseResource;
}
export interface DeleteHpcApplicationResult {}
export interface ListSoftwareStackRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    disabled_also?: boolean;
    project_id?: string;
}
export interface SignOutResult {}
export interface JobUpdates {
    queued: JobUpdate[];
    modified: JobUpdate[];
    running: JobUpdate[];
}
export interface CreateUserResult {
    user?: User;
}
export interface GetModuleSettingsResult {
    settings?: unknown;
}
export interface UpdateModuleSettingsResult {}
export interface DeleteGroupRequest {
    group_name?: string;
}
export interface ListAllowedInstanceTypesForSessionResponse {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: unknown[];
    filters?: SocaFilter[];
}
export interface CheckHpcLicenseResourceAvailabilityRequest {
    name?: string;
}
export interface ResumeSessionsResponse {
    failed?: VirtualDesktopSession[];
    success?: VirtualDesktopSession[];
}
export interface GetPermissionProfileResponse {
    profile?: VirtualDesktopPermissionProfile;
}
export interface DownloadFilesRequest {
    files?: string[];
}
export interface UpdateQueueProfileResult {
    queue_profile?: HpcQueueProfile;
}
export interface UpdateEmailTemplateRequest {
    template?: EmailTemplate;
}
export interface UpdateProjectRequest {
    project?: Project;
}
export interface UpdateFileSystemRequest {
    filesystem_name: string;
    filesystem_title?: string;
    projects?: string[];
}
export interface ListSupportedOSRequest {}
export interface ListUsersInGroupResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: User[];
    filters?: SocaFilter[];
}

export interface ListFileSystemsForProjectResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: FileSystem[];
    filters?: SocaFilter[];
}

export interface SetParamResult {
    value?: unknown;
    refresh?: boolean;
}
export interface DisableProjectResult {}
export interface CreateEmailTemplateRequest {
    template?: EmailTemplate;
}
export interface ForgotPasswordRequest {
    client_id?: string;
    username?: string;
}
export interface GetSessionInfoResponse {
    session?: VirtualDesktopSession;
}
export interface ListPermissionsResponse {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: VirtualDesktopSessionPermission[];
    filters?: SocaFilter[];
}
export interface GetHpcLicenseResourceRequest {
    name?: string;
}
export interface DisableUserResult {
    user?: User;
}
export interface GlobalSignOutRequest {
    username?: string;
}
export interface GetJobResult {
    job?: SocaJob;
}
export interface GetUserRequest {
    username?: string;
}
export interface ListHpcApplicationsRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    lite?: boolean;
}
export interface OpenPBSInfo {
    name?: string;
    version?: string;
    mom_private_dns?: string;
    mom_port?: number;
}
export interface ListClusterHostsRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    instance_ids?: string[];
}
export interface CreateSessionRequest {
    session?: VirtualDesktopSession;
}
export interface DownloadFilesResult {
    download_url?: string;
}
export interface EnableQueueProfileRequest {
    queue_profile_id?: string;
    queue_profile_name?: string;
}
export interface DeleteGroupResult {}
export interface CreateQueueProfileResult {
    queue_profile?: HpcQueueProfile;
    validation_errors?: JobValidationResult;
}
export interface CheckHpcLicenseResourceAvailabilityResult {
    available_count?: number;
}
export interface ListSessionsRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
}
export interface UpdatePermissionProfileRequest {
    profile?: VirtualDesktopPermissionProfile;
}
export interface UpdateProjectResult {
    project?: Project;
}
export interface UpdateFileSystemResult {}
export interface AddAdminUserRequest {
    username?: string;
}
export interface ListQueueProfilesRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    lite?: boolean;
}
export interface ListGroupsResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: Group[];
    filters?: SocaFilter[];
}
export interface ProvisioningCapacityInfo {
    desired_capacity?: number;
    group_capacity?: number;
    target_capacity?: number;
    existing_capacity?: number;
    provisioned_capacity?: number;
    idle_capacity?: number;
    busy_capacity?: number;
    pending_capacity?: number;
    total_instances?: number;
    idle_instances?: number;
    busy_instances?: number;
    pending_instances?: number;
    max_provisioned_instances?: number;
    max_provisioned_capacity?: number;
    comment?: string;
    error_code?: string;
}
export interface GetParamsRequest {
    module?: string;
    format?: string;
}
export interface UpdateSessionRequest {
    session?: VirtualDesktopSession;
}
export interface GetUserProjectsRequest {
    username?: string;
    exclude_disabled?: boolean;
}
export interface CreateEmailTemplateResult {
    template?: EmailTemplate;
}
export interface ForgotPasswordResult {}
export interface SocaPayload {}
export interface ListSoftwareStackResponse {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: VirtualDesktopSoftwareStack[];
    filters?: SocaFilter[];
}
export interface ReadFileRequest {
    file?: string;
}
export interface ListNodesRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    instance_ids?: string[];
    instance_types?: string[];
    job_id?: string;
    job_group?: string;
    compute_stack?: string;
    queue_type?: string;
    states?: SocaComputeNodeState[];
}
export interface ListClusterHostsResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: unknown[];
    filters?: SocaFilter[];
}
export interface GetHpcLicenseResourceResult {
    license_resource?: HpcLicenseResource;
}
export interface CreateSoftwareStackFromSessionRequest {
    session?: VirtualDesktopSession;
    new_software_stack?: VirtualDesktopSoftwareStack;
}
export interface CreateSessionResponse {
    session?: VirtualDesktopSession;
}
export interface StopSessionRequest {
    sessions?: VirtualDesktopSession[];
}
export interface GlobalSignOutResult {}
export interface CreateHpcApplicationRequest {
    application?: HpcApplication;
}
export interface SocaComputeNodeResources {
    cpus?: number;
    gpus?: number;
    memory?: SocaMemory;
}
export interface EnableQueueProfileResult {}
export interface ListEmailTemplatesResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: EmailTemplate[];
    filters?: SocaFilter[];
}
export interface DeleteJobResult {}
export interface GetUserResult {
    user?: User;
}
export interface DeleteFilesRequest {
    files?: string[];
}
export interface SocaUserInputTag {
    name?: string;
    title?: string;
    description?: string;
    markdown?: string;
    unicode?: string;
    ascii?: string;
    icon?: string;
}
export interface EnableGroupRequest {
    group_name?: string;
}
export interface GetParamDefaultRequest {
    module?: string;
    param?: string;
    reset?: boolean;
}
export interface ListUsersRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
}
export interface QueuedJob {
    priority?: number;
    job_id: string;
    job_group: string;
    deleted?: boolean;
    processed?: boolean;
    capacity_added?: boolean;
}
export interface ListSupportedOSResponse {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: string[];
    filters?: SocaFilter[];
}
export interface DeleteProjectRequest {
    project_name?: string;
    project_id?: string;
}
export interface SocaBatchResponsePayload {
    failed?: unknown[];
    success?: unknown[];
}
export interface AddUserToGroupRequest {
    usernames?: string[];
    group_name?: string;
}
export interface UpdatePermissionProfileResponse {
    profile?: VirtualDesktopPermissionProfile;
}
export interface GetParamsResult {
    params?: {
        [k: string]: unknown;
    };
    yaml?: string;
}
export interface GetEmailTemplateRequest {
    name?: string;
}
export interface ChangePasswordRequest {
    username?: string;
    old_password?: string;
    new_password?: string;
}
export interface JobValidationDebugEntry {
    title?: string;
    name?: string;
    description?: string;
    valid?: boolean;
    user_value?: unknown;
    job_value?: unknown;
    default_value?: unknown;
}
export interface DescribeInstanceTypesRequest {}
export interface DescribeServersRequest {}
export interface GetUserProjectsResult {
    projects?: Project[];
}
export interface VirtualDesktopSessionBatchResponsePayload {
    failed?: VirtualDesktopSession[];
    success?: VirtualDesktopSession[];
}
export interface DisableQueueProfileRequest {
    queue_profile_id?: string;
    queue_profile_name?: string;
}
export interface BatchCreateSessionRequest {
    sessions?: VirtualDesktopSession[];
}
export interface DeleteSessionResponse {
    failed?: VirtualDesktopSession[];
    success?: VirtualDesktopSession[];
}
export interface UpdateHpcLicenseResourceRequest {
    license_resource?: HpcLicenseResource;
    dry_run?: boolean;
}
export interface CreateSoftwareStackFromSessionResponse {
    software_stack?: VirtualDesktopSoftwareStack;
}
export interface StopSessionResponse {
    failed?: VirtualDesktopSession[];
    success?: VirtualDesktopSession[];
}
export interface DeleteFilesResult {}
export interface CreateHpcApplicationResult {
    application?: HpcApplication;
}
export interface ModifyUserRequest {
    user?: User;
    email_verified?: boolean;
}
export interface EnableGroupResult {}
export interface GetParamDefaultResult {
    default?: unknown;
}
export interface DeleteProjectResult {}
export interface ListSupportedGPURequest {}
export interface SocaListingPayload {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
}
export interface RebootSessionResponse {
    failed?: VirtualDesktopSession[];
    success?: VirtualDesktopSession[];
}
export interface ListUsersInGroupRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
    group_names?: string[];
}

export interface ListFileSystemsForProjectRequest {
    project_name?: string;
    project_id?: string;
}

export interface ListSecurityGroupsRequest {}

export interface ListSecurityGroupsResult {
    security_groups?: SecurityGroup[];
}

export interface ListPoliciesRequest {}

export interface ListPoliciesResult {
    policies?: Policy[]
}

export interface ListQueueProfilesResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: HpcQueueProfile[];
    filters?: SocaFilter[];
}
export interface SocaInputParamSpec {
    name?: string;
    version?: string;
    tags?: SocaUserInputTag[];
    modules?: SocaUserInputModuleMetadata[];
    params?: SocaUserInputParamMetadata[];
}
export interface AddUserToGroupResult {}
export interface DescribeInstanceTypesResult {
    instance_types: unknown[];
}
export interface UpdateTitleRequest {
    title?: string;
}
export interface UpdateTitleResult {}
export interface UpdateSubtitleRequest {
    subtitle?: string;
}
export interface UpdateSubtitleResult {}
export interface UpdateCopyrightTextRequest {
    copyright_text?: string;
}
export interface UpdateCopyrightTextResult {}
export interface CreatePermissionProfileRequest {
    profile?: VirtualDesktopPermissionProfile;
}
export interface ChangePasswordResult {}
export interface JobParameterInfo {
    name?: string;
    title?: string;
    description?: string;
    provider_names?: {
        [k: string]: string;
    };
}
export interface SocaComputeNode {
    host?: string;
    cluster_name?: string;
    cluster_version?: string;
    states?: SocaComputeNodeState[];
    queue_type?: string;
    queue?: string;
    provisioning_time?: string;
    last_used_time?: string;
    last_state_changed_time?: string;
    availability_zone?: string;
    subnet_id?: string;
    instance_id?: string;
    instance_type?: string;
    instance_ami?: string;
    instance_profile?: string;
    architecture?: string;
    scheduler_info?: SocaSchedulerInfo;
    sharing?: SocaComputeNodeSharing;
    job_id?: string;
    job_group?: string;
    scaling_mode?: SocaScalingMode;
    keep_forever?: boolean;
    terminate_when_idle?: number;
    compute_stack?: string;
    stack_id?: string;
    lifecyle?: string;
    tenancy?: string;
    spot_fleet_request?: string;
    auto_scaling_group?: string;
    spot?: boolean;
    spot_price?: SocaAmount;
    base_os?: string;
    enable_placement_group?: boolean;
    enable_ht_support?: boolean;
    keep_ebs_volumes?: boolean;
    root_storage_size?: SocaMemory;
    scratch_storage_size?: SocaMemory;
    scratch_storage_iops?: number;
    enable_efa_support?: boolean;
    force_reserved_instances?: boolean;
    enable_system_metrics?: boolean;
    enable_anonymous_metrics?: boolean;
    fsx_lustre?: SocaFSxLustreConfig;
    resources_available?: SocaComputeNodeResources;
    resources_assigned?: SocaComputeNodeResources;
    launch_time?: string;
    termination_time?: string;
    terminated?: boolean;
    jobs?: string[];
}
export interface DisableQueueProfileResult {}
export interface DescribeServersResponse {
    response?: {
        [k: string]: unknown;
    };
}
export interface VirtualDesktopApplicationProfile {}
export interface GetEmailTemplateResult {
    template?: EmailTemplate;
}
export interface ListNodesResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: SocaComputeNode[];
    filters?: SocaFilter[];
}
export interface RemoveAdminUserRequest {
    username?: string;
}
export interface GetJobRequest {
    job_id?: string;
}
export interface GetModuleMetadataRequest {
    module?: string;
}
export interface ResumeSessionsRequest {
    sessions?: VirtualDesktopSession[];
}
export interface CreateFileRequest {
    cwd?: string;
    filename?: string;
    is_folder?: boolean;
}
export interface GetHpcApplicationRequest {
    application_id?: string;
}
export interface DisableGroupRequest {
    group_name?: string;
}
export interface UpdateHpcLicenseResourceResult {
    license_resource?: HpcLicenseResource;
}
export interface TailFileRequest {
    file?: string;
    line_count?: number;
    next_token?: string;
}
export interface BatchCreateSessionResponse {
    failed?: VirtualDesktopSession[];
    success?: VirtualDesktopSession[];
}
export interface CreateSoftwareStackRequest {
    software_stack?: VirtualDesktopSoftwareStack;
}
export interface RebootSessionRequest {
    sessions?: VirtualDesktopSession[];
}
export interface ModifyUserResult {
    user?: User;
}
export interface GetInstanceTypeOptionsRequest {
    enable_ht_support?: boolean;
    instance_types?: string[];
    queue_name?: string;
    queue_profile_name?: string;
}
export interface GetSessionScreenshotResponse {
    failed?: VirtualDesktopSessionScreenshot[];
    success?: VirtualDesktopSessionScreenshot[];
}
export interface RemoveUserFromGroupRequest {
    usernames?: string[];
    group_name?: string;
}
export interface DeleteQueueProfileRequest {
    queue_profile_id?: string;
    queue_profile_name?: string;
    delete_queues?: boolean;
}
export interface ResetPasswordRequest {
    username?: string;
}
export interface ListProjectsRequest {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
}
export interface ListOnboardedFileSystemsRequest {
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: (SocaBaseModel | unknown)[];
    filters?: SocaFilter[];
}

export interface ListFileSystemsInVPCRequest {}

export interface ListFileSystemsInVPCResult {
    efs: EFSFileSystem[];
    fsx_ontap: FSxONTAPFileSystem[];
    fsx_lustre: FSxLUSTREFileSystem[];
}

export interface DescribeSessionsRequest {
    sessions?: VirtualDesktopSession[];
}
export interface CreatePermissionProfileResponse {
    profile?: VirtualDesktopPermissionProfile;
}
export interface ProvisionAlwaysOnNodesRequest {
    project_name?: string;
    queue_profile_name?: string;
    queue_name?: string;
    owner?: string;
    params?: SocaJobParams;
}
export interface ListUsersResult {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: User[];
    filters?: SocaFilter[];
}
export interface ListSupportedGPUResponse {
    paginator?: SocaPaginator;
    sort_by?: SocaSortBy;
    date_range?: SocaDateRange;
    listing?: string[];
    filters?: SocaFilter[];
}
export interface ConfigureSSORequest {
    provider_name: string;
    provider_type: string;
    provider_email_attribute: string;
    refresh_token_validity_hours?: number;
    oidc_client_id?: string;
    oidc_client_secret?: string;
    oidc_issuer?: string;
    oidc_attributes_request_method?: string;
    oidc_authorize_scopes?: string;
    oidc_authorize_url?: string;
    oidc_token_url?: string;
    oidc_attributes_url?: string;
    oidc_jwks_uri?: string;
    saml_metadata_url?: string;
    saml_metadata_file?: string;
}
export interface ConfigureSSOResponse {}
export interface GetSoftwareStackInfoRequest {
    stack_id?: string;
    base_os?: string
}
export interface AddAdminUserResult {
    user?: User;
}
export interface SocaJobPlacement {
    arrangement?: SocaJobPlacementArrangement;
    sharing?: SocaJobPlacementSharing;
    grouping?: string;
}

export interface AddFileSystemToProjectRequest {
    project_name?: string;
    project_id?: string;
    filesystem_id?: string;
    filesystem_name?: string;
}

export interface AddFileSystemToProjectResult {}

export interface RemoveFileSystemFromProjectRequest {
    project_name?: string;
    project_id?: string;
    filesystem_id?: string;
    filesystem_name?: string;
}

export interface RemoveFileSystemFromProjectResult {}

interface CommonCreateFileSystemRequest {
    filesystem_name?: string;
    filesystem_title?: string;
    projects?: string[];
}
export interface CreateEFSFileSystemRequest extends CommonCreateFileSystemRequest {
    mount_directory?: string;
    subnet_id_1?: string;
    subnet_id_2?: string;
}

export interface CreateONTAPFileSystemRequest extends CommonCreateFileSystemRequest {
    mount_directory?: string;
    mount_drive?: string;
    primary_subnet?: string;
    deployment_type?: string;
    standby_subnet?: string;
    storage_capacity?: number;
    file_share_name?: string;
    volume_security_style?: string;
}

export interface CreateEFSFileSystemResult {}

export interface CreateONTAPFileSystemResult {}

export interface CommonOnboardFileSystemRequest {
    filesystem_name: string;
    filesystem_title: string;
    filesystem_id: string;
}
export interface OnboardEFSFileSystemRequest extends CommonOnboardFileSystemRequest {
    mount_directory: string;
}
export interface OnboardONTAPFileSystemRequest extends CommonOnboardFileSystemRequest {
    mount_directory?: string;
    mount_drive?: string;
    svm_id: string;
    volume_id: string;
    file_share_name?: string;
}
export interface OnboardLUSTREFileSystemRequest extends CommonOnboardFileSystemRequest {
    mount_directory: string;
}

export interface OnboardS3BucketRequest  {
    object_storage_title: string;
    bucket_arn: string;
    read_only: boolean;
    custom_bucket_prefix?: string;
    mount_directory: string;
    iam_role_arn?: string;
    projects?: string[];
}

export interface OnboardS3BucketResult  {
    filesystem_name: string;
}

export interface OnboardFileSystemResult {}

export interface RemoveFileSystemRequest  {
    filesystem_name: string;
}

export interface RemoveFileSystemResult  {}

export interface ConfigureQUICRequest {
    enable: boolean;
}

export interface ConfigureQUICResult {
    result?: string;
}
