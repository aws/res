# Roadmap

2026.09 is the final AWS release of Research and Engineering Studio. No further AWS release follows it.

This document lists the features customers requested and what 2026.09 provides.

---

## Portal usability

**Asked for:** default values on the desktop launch form, a searchable session list, search within teams,
groups and users, showing which project a desktop belongs to, hiding operating systems a deployment doesn't
use, session state on the dashboard, the desktop name in the DCV client, a maintenance banner,
per-deployment styling, timezone settings, and a confirmation dialog before terminating a desktop.

**In 2026.09:** search within teams, groups and users. The launch form has no configurable defaults, and
timezone is derived from the deployment region rather than being a setting.

## Desktop lifecycle and capacity

**Asked for:** faster provisioning through pre-warmed capacity, EC2 Capacity Block support, queueing a
launch when capacity is unavailable, instance-type diversification, preventing users from terminating their
own desktops, restarting a desktop stuck in an error state, desktop pools, changing instance type on an
existing session, administrator-set default schedules, and EFA on desktops.

**In 2026.09:** idle detection with auto-stop, hibernation on Linux, desktop expiry, and changing the
instance type of an existing session by stopping it, changing the type and starting it again. Desktops
provision through EC2 Fleet. A smart retry mechanism retries a launch when EC2 returns insufficient
capacity, controlled by the `vdc.dcv_session.smart_retry.enabled` cluster setting.

**Not in 2026.09:** pre-warmed pools, Capacity Blocks, launch queueing, desktop pools, preventing user
termination, restarting an errored desktop, EFA.

## Identity, directory and authentication

**Asked for:** Microsoft Entra ID, directory options other than AWS Managed Microsoft AD, group nesting,
multi-forest and dual-domain support, root and child domains, mapping OIDC and SAML claims to internal
attributes, identity-provider-initiated SSO, AD synchronization without simple bind, configurable AD sync
frequency, authenticating AD members by group or attribute rather than by organizational unit, custom
domain-join logic, password rotation and expiry checks, and passwordless access.

**In 2026.09:** SSO through Cognito with OIDC and SAML, group membership synchronization from AD, reuse of
an existing Cognito user pool, and configurable user mapping.

Entra ID is not supported. RES expects a single Microsoft AD forest.

## Storage and file access

**Asked for:** FSx for NetApp ONTAP as the shared home filesystem and managed from the portal, FSx for
Windows File Server, S3 as a mountable filesystem, EFS access points, a read-only filesystem option,
deploying without the shared EFS filesystem, home directory isolation for privileged users, moving data
between storage locations, and EBS options at launch with user self-service expansion.

**In 2026.09:** S3 bucket and prefix mounting, multiple volumes from a single ONTAP filesystem, removal of
the shared EFS or FSx filesystem, and a file browser that administrators can disable per deployment.

**Not in 2026.09:** ONTAP as shared home, ONTAP portal management, FSx for Windows, EFS access points, read-only
filesystems, home directory isolation, EBS self-service expansion.

## Network topology, accounts and regions

**Asked for:** deployment into shared subnets, administrators enforcing which subnets desktops use, a
subnet group for desktops, removing the two-availability-zone requirement, projects in member accounts,
multi-account deployment, a private hosted zone option, a pre-deployed API Gateway endpoint in shared
network infrastructure, and proxy configuration for isolated VPCs.

**In 2026.09:** deployment into an existing VPC, private subnets, a customizable CIDR for the
infrastructure stack, 18 commercial regions and two GovCloud regions, and an IAM resource path and prefix.

**Not in 2026.09:** shared subnets, subnet enforcement, subnet groups, single-AZ deployment, projects in member
accounts, private hosted zones, pre-deployed API Gateway endpoints.

Isolated-VPC deployments need a proxy, because Cognito has no VPC endpoint. See
`docs/reference/first-run.md`.

## Security, compliance and isolation

**Asked for:** an isolated desktop mode with SSH and file transfer disabled, administrator approval for
file uploads and downloads, large file transfer inside isolated networks, WCAG and ADA conformance
reporting, terms and conditions acceptance, login notification, control over sudo membership, ACM for
desktop certificate management, and cleanup of resources on instance termination.

**In 2026.09:** disabling the file browser, disabling deployment-wide file sharing, DCV
permission profiles including a deployment-wide maximum, disabling SSH and SSM access to desktops, and
disabling the bastion host.

**Not in 2026.09:** administrator approval workflows for file transfer, WCAG and ADA reporting, terms and
conditions, login notification, sudo membership control, ACM-managed desktop certificates.

## Cost, budget and quota

**Asked for:** per-user budget and expense tracking, exposing budget information to users and
non-administrators, creating budgets in the portal, budgets in GovCloud, stopping or terminating resources
when a budget is exceeded, showing the cost of a selected instance type before launch, cost visualization
across research spend, a utilization dashboard, and a maximum desktop count per project.

**In 2026.09:** project budgets, enforced at session creation when the cluster setting
`vdc.controller.enforce_project_budgets` is enabled. It defaults to off.

Budget information is not exposed to non-administrators.

## Software stacks and AMIs

**Asked for:** AMI lifecycle management within a software stack, just-in-time stack and AMI creation,
encrypted AMIs with a customer-managed KMS key, cross-account encrypted AMIs, specifying instance details
when creating a stack from a session, and expanded permissions for image building.

**In 2026.09:** automated image building, hardened AMI support, RHEL custom AMIs for infrastructure hosts,
an SSM parameter alias for AMIs, restricting instance types per software stack, registering allowed
instance types and families during stack creation, and deleting software stacks from the portal.

**Not in 2026.09:** AMI lifecycle management within a stack, just-in-time creation, customer-managed KMS keys,
cross-account encrypted AMIs.

The pinned AMI tables in `source/idea/infrastructure/resources/config/` were last refreshed for 2026.09.
The pins age from that date.

## Automation and API

**Asked for:** an API covering core administrative functions, an OpenAPI description, CDK support, a
Terraform deployment template, AWS Service Catalog integration, programmatic session creation, managed
stack updates, and in-place upgrades.

**In 2026.09:** a REST API with an OpenAPI description at
`source/idea/backend/api/openapi/RES.openapi.yaml`, served by a Lambda function behind the load balancer.
It has 26 operations, and every path sits under `/res/virtual-desktop/` or `/res/virtual-desktop-utils/`.
Sessions, software stacks, permission profiles and session permissions are covered.

**Not in 2026.09:** an API description for administrative objects. Projects, users, groups, filesystems and
cluster settings are reachable only through the namespace-style endpoint at `/cluster-manager/api/v1`,
which has no OpenAPI description and isn't documented. Also not there: CDK or Terraform deployment, Service
Catalog integration, in-place upgrades.

## Tagging and governance

**Asked for:** custom tags applied to every deployed resource, the installer propagating tags to everything
it creates, tags on desktop EBS volumes, snapshots and network interfaces, automatic tagging of desktops by
the person who created them, project-level tagging, and housekeeping of disabled resources.

**In 2026.09:** project tags applied to instance volumes, custom tag population during deployment, and
overwriting RES-applied tags.

**Not in 2026.09:** tagging by creator, tagging of snapshots and network interfaces, housekeeping of disabled
resources.

## HPC and adjacent AWS services

**Asked for:** PBS scheduler support, Slurm partition creation from the portal, Slurm and infrastructure
resource tagging, job submission from the portal, SageMaker, Braket, Bedrock, Amazon Q, and Open Data and
Data Exchange integration.

**In 2026.09:** FSx for Lustre can be onboarded as a shared filesystem. RES does not integrate with
AWS Parallel Computing Service.

The rest are listed under Other ideas below.

## Operating system support

**In 2026.09:** Amazon Linux 2023 on x86-64 and arm64, Ubuntu 22.04, Ubuntu 24.04, RHEL 9, Windows Server,
and Windows 10 and 11 desktops. Rocky Linux 9 is in the AMI configuration but is not a base software
stack.

**Not in 2026.09:** Alma Linux, Fedora, other distributions.

## Observability

**Asked for:** Active Directory synchronization status on the environment status page, visibility into why
a desktop is provisioning slowly or sitting in an error state, a resource utilization dashboard, and
creating AWS Support tickets from the portal.

**In 2026.09:** none of these.

Diagnostic data is in CloudWatch log groups, and for the shell stage of desktop bootstrap, in logs that
exist only on the instance. `docs/operate/diagnosing-failures.md` covers what is available and where.

## Scale and availability

**Asked for:** multi-node controllers and brokers, and controller placement within a single availability
zone.

**In 2026.09:** the virtual-desktop controller host is removed and its work runs in Lambda functions. The
DCV broker runs as Lambda-based session management. Large deployments have hit API throttling. The
scaling levers in 2026.09 are the connection gateway and session management;
`docs/operate/diagnosing-failures.md` covers the symptoms.

---

## Other ideas

- **In-place upgrades.** Upgrading means deploying a new environment.
- **Multi-account deployment**, and multi-account with multiple identity providers.
- **Job submission from the portal.**
- **PBS scheduler support**, **SageMaker**, **Braket**, **Bedrock and AI features**, **Amazon Q**, **Open
  Data and Data Exchange integration**.
- **Terraform deployment templates.**
- **Multi-node controllers and brokers.**
- **Desktop pools** and **expanded desktop sharing**.
- **AWS Support ticket creation from the portal.**
- **Operating systems beyond the supported set.**
- **AD password change from the login screen.**
