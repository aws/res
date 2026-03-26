//  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//  SPDX-License-Identifier: Apache-2.0
$version: "2.0"

namespace res.virtualdesktop

@documentation("Supported base operating systems for virtual desktops")
enum VirtualDesktopBaseOs {
    @documentation("Amazon Linux 2")
    AMAZON_LINUX2 = "amazonlinux2"

    @documentation("Amazon Linux 2023")
    AMAZON_LINUX2023 = "amzn2023"

    @documentation("Red Hat Enterprise Linux 8")
    RHEL8 = "rhel8"

    @documentation("Red Hat Enterprise Linux 9")
    RHEL9 = "rhel9"

    @documentation("Ubuntu 22.04 LTS")
    UBUNTU2204 = "ubuntu2204"

    @documentation("Ubuntu 24.04 LTS")
    UBUNTU2404 = "ubuntu2404"

    @documentation("Rocky Linux 9")
    ROCKY_LINUX9 = "rocky9"

    @documentation("Microsoft Windows")
    WINDOWS = "windows"
}

@documentation("Supported GPUs for virtual desktops")
enum VirtualDesktopGpu {
    @documentation("No GPU")
    NO_GPU = "NO_GPU"

    @documentation("NVIDIA")
    NVIDIA = "NVIDIA"

    @documentation("AMD")
    AMD = "AMD"
}

@documentation("Supported architectures for virtual desktops")
enum VirtualDesktopArchitecture {
    @documentation("x86_64 architecture")
    X86_64 = "x86_64"

    @documentation("ARM64 architecture")
    ARM64 = "arm64"
}

@documentation("Virtual desktop tenancy options")
enum VirtualDesktopTenancy {
    @documentation("Default tenancy")
    DEFAULT = "default"

    @documentation("Dedicated tenancy")
    DEDICATED = "dedicated"

    @documentation("Host tenancy")
    HOST = "host"
}

@documentation("Virtual desktop affinity options")
enum VirtualDesktopAffinity {
    @documentation("Default affinity")
    DEFAULT = "default"

    @documentation("Host affinity")
    HOST = "host"
}

@documentation("Virtual desktop schedule types")
enum VirtualDesktopScheduleType {
    @documentation("Working Hours")
    WORKING_HOURS = "WORKING_HOURS"

    @documentation("Stop All Day")
    STOP_ALL_DAY = "STOP_ALL_DAY"

    @documentation("Start All Day")
    START_ALL_DAY = "START_ALL_DAY"

    @documentation("Custom Schedule")
    CUSTOM_SCHEDULE = "CUSTOM_SCHEDULE"

    @documentation("No Schedule")
    NO_SCHEDULE = "NO_SCHEDULE"
}

@documentation("Virtual desktop session state")
enum VirtualDesktopSessionState {
    @documentation("Provisioning")
    PROVISIONING = "PROVISIONING"

    @documentation("Creating")
    CREATING = "CREATING"

    @documentation("Initializing")
    INITIALIZING = "INITIALIZING"

    @documentation("Ready")
    READY = "READY"

    @documentation("Resuming")
    RESUMING = "RESUMING"

    @documentation("Stopping")
    STOPPING = "STOPPING"

    @documentation("Stopped")
    STOPPED = "STOPPED"

    @documentation("Stopped due to idle timeout")
    STOPPED_IDLE = "STOPPED_IDLE"

    @documentation("Error state")
    ERROR = "ERROR"

    @documentation("Deleting")
    DELETING = "DELETING"

    @documentation("Deleted")
    DELETED = "DELETED"
}

@documentation("Virtual desktop session type")
enum VirtualDesktopSessionType {
    @documentation("Console session")
    CONSOLE = "CONSOLE"

    @documentation("Virtual session")
    VIRTUAL = "VIRTUAL"
}

@documentation("Day of the week")
enum DayOfWeek {
    @documentation("Monday")
    MONDAY = "monday"

    @documentation("Tuesday")
    TUESDAY = "tuesday"

    @documentation("Wednesday")
    WEDNESDAY = "wednesday"

    @documentation("Thursday")
    THURSDAY = "thursday"

    @documentation("Friday")
    FRIDAY = "friday"

    @documentation("Saturday")
    SATURDAY = "saturday"

    @documentation("Sunday")
    SUNDAY = "sunday"
}

@documentation("Memory specification structure")
structure ResMemory {
    @documentation("Memory value")
    value: Double

    @documentation("Memory unit (e.g., GB, MB)")
    unit: String
}

@documentation("Project information structure")
structure Project {
    @documentation("Project identifier")
    @jsonName("project_id")
    id: String

    @documentation("Project name")
    name: String

    @documentation("Project title")
    title: String

    @documentation("Project description")
    description: String
}

@documentation("Virtual desktop placement configuration")
structure VirtualDesktopPlacement {
    @documentation("Placement affinity")
    affinity: VirtualDesktopAffinity

    @documentation("Instance tenancy")
    tenancy: VirtualDesktopTenancy

    @documentation("Dedicated host ID")
    @jsonName("host_id")
    hostId: String

    @documentation("Host resource group ARN")
    @jsonName("host_resource_group_arn")
    hostResourceGroupArn: String
}

@documentation("Virtual desktop software stack configuration")
structure VirtualDesktopSoftwareStack {
    @documentation("Unique identifier for the software stack")
    @jsonName("stack_id")
    stackId: String

    @documentation("Base operating system")
    @jsonName("base_os")
    @required
    baseOs: VirtualDesktopBaseOs

    @documentation("Human-readable name for the software stack")
    @required
    name: String

    @documentation("Description of the software stack")
    description: String

    @documentation("Timestamp when the stack was created")
    @jsonName("created_on")
    createdOnStr: String

    @documentation("Timestamp when the stack was last updated")
    @jsonName("updated_on")
    updatedOnStr: String

    @documentation("Amazon Machine Image (AMI) ID")
    @jsonName("ami_id")
    @required
    amiId: String

    @documentation("Reason for any failure in stack creation or update")
    @jsonName("failure_reason")
    failureReason: String

    @documentation("Whether the software stack is enabled")
    enabled: Boolean

    @documentation("Minimum storage requirement")
    @jsonName("min_storage")
    @required
    minStorage: ResMemory

    @documentation("Minimum RAM requirement")
    @jsonName("min_ram")
    @required
    minRam: ResMemory

    @documentation("CPU architecture")
    architecture: VirtualDesktopArchitecture

    @documentation("GPU type")
    @required
    gpu: VirtualDesktopGpu

    @documentation("Instance placement configuration")
    placement: VirtualDesktopPlacement

    @documentation("Version number of the software stack")
    version: Integer

    @documentation("List of projects associated with this software stack")
    projects: ProjectList

    @documentation("List of allowed EC2 instance types")
    @jsonName("allowed_instance_types")
    allowedInstanceTypes: InstanceTypeList
}

@documentation("List of projects")
list ProjectList {
    member: Project
}

@documentation("List of EC2 instance types")
list InstanceTypeList {
    member: String
}

@documentation("List of strings")
list StringList {
    member: String
}

@documentation("List of tag objects")
list TagList {
    member: Document
}

@documentation("Virtual desktop server configuration")
structure VirtualDesktopServer {
    @documentation("Unique server identifier")
    @jsonName("server_id")
    serverId: String

    @documentation("IDEA session ID associated with this server")
    @jsonName("idea_session_id")
    ideaSessionId: String

    @documentation("Session owner")
    @jsonName("idea_session_owner")
    ideaSessionOwner: String

    @documentation("EC2 instance ID")
    @jsonName("instance_id")
    instanceId: String

    @documentation("EC2 instance type")
    @jsonName("instance_type")
    instanceType: String

    @documentation("Private IP address")
    @jsonName("private_ip")
    privateIp: String

    @documentation("Private DNS name")
    @jsonName("private_dns_name")
    privateDnsName: String

    @documentation("Public IP address")
    @jsonName("public_ip")
    publicIp: String

    @documentation("Public DNS name")
    @jsonName("public_dns_name")
    publicDnsName: String

    @documentation("Server availability status")
    availability: String

    @documentation("Reason for server unavailability")
    @jsonName("unavailability_reason")
    unavailabilityReason: String

    @documentation("Number of console sessions")
    @jsonName("console_session_count")
    consoleSessionCount: Integer

    @documentation("Number of virtual sessions")
    @jsonName("virtual_session_count")
    virtualSessionCount: Integer

    @documentation("Maximum concurrent sessions per user")
    @jsonName("max_concurrent_sessions_per_user")
    maxConcurrentSessionsPerUser: Integer

    @documentation("Maximum virtual sessions")
    @jsonName("max_virtual_sessions")
    maxVirtualSessions: Integer

    @documentation("Server state")
    state: String

    @documentation("Whether the server is locked")
    locked: Boolean

    @documentation("Root volume size")
    @jsonName("root_volume_size")
    rootVolumeSize: ResMemory

    @documentation("Root volume IOPS")
    @jsonName("root_volume_iops")
    rootVolumeIops: Integer

    @documentation("Instance profile ARN")
    @jsonName("instance_profile_arn")
    instanceProfileArn: String

    @documentation("Security group IDs")
    @jsonName("security_groups")
    securityGroups: StringList

    @documentation("Subnet ID")
    @jsonName("subnet_id")
    subnetId: String

    @documentation("Key pair name")
    @jsonName("key_pair_name")
    keyPairName: String

    @documentation("Whether the server is idle")
    @jsonName("is_idle")
    isIdle: Boolean
}

@documentation("Virtual desktop schedule for a specific day")
structure VirtualDesktopSchedule {
    @documentation("Schedule identifier")
    @jsonName("schedule_id")
    scheduleId: String

    @documentation("IDEA session ID")
    @jsonName("idea_session_id")
    ideaSessionId: String

    @documentation("Session owner")
    @jsonName("idea_session_owner")
    ideaSessionOwner: String

    @documentation("Day of the week")
    @jsonName("day_of_week")
    dayOfWeek: DayOfWeek

    @documentation("Start up time of day (e.g. 09:00)")
    @jsonName("start_up_time")
    startUpTimeOfDay: String

    @documentation("Shut down time of day (e.g. 17:30)")
    @jsonName("shut_down_time")
    shutDownTimeOfDay: String

    @documentation("Schedule type")
    @jsonName("schedule_type")
    scheduleType: VirtualDesktopScheduleType
}

@documentation("Virtual desktop week schedule")
structure VirtualDesktopWeekSchedule {
    @documentation("Monday schedule")
    monday: VirtualDesktopSchedule

    @documentation("Tuesday schedule")
    tuesday: VirtualDesktopSchedule

    @documentation("Wednesday schedule")
    wednesday: VirtualDesktopSchedule

    @documentation("Thursday schedule")
    thursday: VirtualDesktopSchedule

    @documentation("Friday schedule")
    friday: VirtualDesktopSchedule

    @documentation("Saturday schedule")
    saturday: VirtualDesktopSchedule

    @documentation("Sunday schedule")
    sunday: VirtualDesktopSchedule
}

@documentation("Virtual desktop session")
structure VirtualDesktopSession {
    @documentation("DCV session identifier")
    @jsonName("dcv_session_id")
    dcvSessionId: String

    @documentation("IDEA session identifier")
    @jsonName("idea_session_id")
    ideaSessionId: String

    @documentation("Base operating system")
    @jsonName("base_os")
    baseOs: VirtualDesktopBaseOs

    @documentation("Session name")
    name: String

    @documentation("Session owner")
    owner: String

    @documentation("Session type")
    type: VirtualDesktopSessionType

    @documentation("Virtual desktop server")
    server: VirtualDesktopServer

    @documentation("Timestamp when the session was created")
    @jsonName("created_on")
    createdOnStr: String

    @documentation("Timestamp when the session was last updated")
    @jsonName("updated_on")
    updatedOnStr: String

    @documentation("Current session state")
    state: VirtualDesktopSessionState

    @documentation("Session description")
    description: String

    @documentation("Software stack configuration")
    @jsonName("software_stack")
    @required
    softwareStack: VirtualDesktopSoftwareStack

    @documentation("Associated project")
    project: Project

    @documentation("Weekly schedule configuration")
    schedule: VirtualDesktopWeekSchedule

    @documentation("Number of active connections")
    @jsonName("connection_count")
    connectionCount: Integer

    @documentation("Force flag")
    force: Boolean

    @documentation("Whether hibernation is enabled")
    @jsonName("hibernation_enabled")
    @required
    hibernationEnabled: Boolean

    @documentation("Whether the session was launched by an admin")
    @jsonName("is_launched_by_admin")
    isLaunchedByAdmin: Boolean

    @documentation("Whether the session is locked")
    locked: Boolean

    @documentation("Session tags")
    tags: TagList

    @documentation("List of allowed logins")
    logins: StringList

    @documentation("Whether the session is idle")
    @jsonName("is_idle")
    isIdle: Boolean

    @documentation("Failure reason for transient API responses")
    @jsonName("failure_reason")
    failureReason: String
}

@documentation("List of virtual desktop sessions")
list VirtualDesktopSessionList {
    member: VirtualDesktopSession
}

@documentation("Id of the profile")
string VirtualDesktopPermissionProfileId

structure VirtualDesktopPermission {
    @documentation("Permission key identifier")
    key: String

    @documentation("Permission display name")
    name: String

    @documentation("Permission description")
    description: String

    @documentation("Whether the permission is enabled")
    enabled: Boolean
}

list VirtualDesktopPermissionList {
    member: VirtualDesktopPermission
}

structure VirtualDesktopPermissionProfile {
    @documentation("Profile identifier")
    @jsonName("profile_id")
    @required
    @length(min: 1)
    profileId: VirtualDesktopPermissionProfileId

    @documentation("Profile title")
    @required
    @length(min: 1)
    title: String

    @documentation("Profile description")
    description: String

    @documentation("List of permissions")
    permissions: VirtualDesktopPermissionList

    // Keep as String until all Permission Profile APIs are migrated
    @documentation("Creation timestamp")
    @jsonName("created_on")
    @suppress(["ShouldHaveUsedTimestamp"])
    createdOn: String

    // Keep as String until all Permission Profile APIs are migrated
    @documentation("Last update timestamp")
    @jsonName("updated_on")
    @suppress(["ShouldHaveUsedTimestamp"])
    updatedOn: String
}

structure VirtualDesktopSessionPermission {
    @required
    @length(min: 1)
    @jsonName("idea_session_id")
    ideaSessionId: String

    @required
    @length(min: 1)
    @jsonName("idea_session_owner")
    ideaSessionOwner: String

    @required
    @length(min: 1)
    @jsonName("idea_session_name")
    ideaSessionName: String

    @required
    @length(min: 1)
    @jsonName("idea_session_instance_type")
    ideaSessionInstanceType: String

    @required
    @length(min: 1)
    @jsonName("idea_session_state")
    ideaSessionState: VirtualDesktopSessionState

    @required
    @length(min: 1)
    @jsonName("idea_session_base_os")
    ideaSessionBaseOs: VirtualDesktopBaseOs

    @required
    @jsonName("idea_session_hibernation_enabled")
    ideaSessionHibernationEnabled: Boolean

    @required
    @length(min: 1)
    @jsonName("idea_session_type")
    ideaSessionType: VirtualDesktopSessionType

    @required
    @jsonName("permission_profile")
    permissionProfile: PermissionProfile

    @required
    @length(min: 1)
    @jsonName("actor_type")
    actorType: String

    @required
    @length(min: 1)
    @jsonName("actor_name")
    actorName: String

    @documentation("Creation timestamp")
    @jsonName("created_on")
    @suppress(["ShouldHaveUsedTimestamp"])
    createdOn: String

    @required
    @length(min: 1)
    @documentation("Creation time for session")
    @jsonName("idea_session_created_on")
    @suppress(["ShouldHaveUsedTimestamp"])
    ideaSessionCreatedOn: String

    @documentation("Last update timestamp")
    @jsonName("updated_on")
    @suppress(["ShouldHaveUsedTimestamp"])
    updatedOn: String

    @documentation("Expiry date")
    @jsonName("expiry_date")
    @suppress(["ShouldHaveUsedTimestamp"])
    expiryDate: String

    @documentation("Reason for any failure in session permission creation or update")
    @jsonName("failure_reason")
    failureReason: String
}

structure PermissionProfile {
    @required
    @jsonName("profile_id")
    profileId: String
}
