# Architecture

> **Note.** This document was written with AI assistance and is not part of the AWS documentation for RES. Treat it as directional: verify anything you depend on against the source tree and your own deployment.

What a RES deployment consists of, where its state is kept, and the order in which a host and a desktop
are created.

## Scope

- §1 what a deployment consists of
- §2 code layout and runtime modules
- §3 where state is kept
- §4 identity
- §5 the host boot sequence
- §6 the desktop launch sequence
- §7 differences between 2026.06 and 2026.09
- §8 components named in other documentation that are not present

These are left out because the repository already declares them: the resource inventory, the install
parameter reference (`source/idea/infrastructure/install/parameters/`), and the API reference, which is
generated from the Smithy models.

For the rules a change must follow, see `docs/develop/code-conventions.md`. To diagnose a failure, see
`docs/operate/diagnosing-failures.md`. To deploy, see `docs/develop/deploying-from-source.md`.

**Markers.** `[verified]` was observed on a running deployment, either RES 2026.06 built entirely from
public source or the 2026.09 release beta, both in `us-west-2`. `[from source]` was read from the 2026.09
tree and not exercised on a running deployment. `[inferred]` is unverified reasoning. Written against
**2026.09**; where 2026.06 differs, §7 says so.

![RES 2026.09 overview: portal and desktop users reach an Application Load Balancer, which routes portal
requests to a backend API on AWS Lambda and portal sign-in to a Cognito user pool. The backend API
launches virtual desktops on Amazon EC2 with Amazon DCV, which are reached through the infrastructure
hosts and read software packages from an S3 staging bucket, home directories from EFS, and POSIX identity
from AWS Managed Microsoft AD. The backend API reads and writes DynamoDB, and the AD sync job and event
handlers read the same directory.](architecture-overview.png)

The overview groups the deployment into the platform VPC, the state it keeps, and the two identity
systems. The diagram below names every component and numbers the sequence in §6.

![RES 2026.09 architecture: portal and desktop users reach an external Application Load Balancer in the
public subnets, which routes /res/* to a backend Lambda; the Lambda authorizes against DynamoDB and
launches virtual desktops through EC2 Fleet in the private subnets alongside the cluster-manager,
vdc-gateway and bastion hosts; a desktop fetches host modules and its application package from the S3
staging bucket at boot, takes POSIX identity from AWS Managed Microsoft AD, mounts EFS home directories,
and serves a DCV session through the vdc-gateway.](architecture.png)

The editable sources are `architecture-overview.html` and `architecture.drawio`.

---

## 1. What a deployment consists of

`[verified]` One CloudFormation install stack creates eight nested stacks.

| Nested stack | Contents |
|---|---|
| `res-base` | DynamoDB tables, shared secrets, base IAM roles |
| `cluster` | Cluster-wide resources, the settings table's initial content, cluster networking |
| `identity` | The Cognito user pool, its clients, and the Lambda functions that connect Cognito to the directory |
| `shared-storage` | Home filesystem mount configuration and onboarded filesystems |
| `cluster-manager` | The cluster manager host, its scaling group, and its application |
| `bastion-host` | The bastion host and its scaling group |
| `vdc` | Connection gateway, desktop provisioning, event handling, and the API |
| `res-finalizer` | Resources created after the others |

`[verified]` CloudFormation reports these names without hyphens: `resbase`, `sharedstorage`,
`clustermanager`, `bastionhost`, `resfinalizer`. The construct identifiers in the source have them.

**Hosts.** `[verified]` 2026.09 runs two long-lived instances, `cluster-manager` and `vdc-gateway`, plus a
bastion host. Each is in its own scaling group of one. There's no in-place update path for a running host:
to replace one, terminate it and let the scaling group launch another.

**Load balancers.** `[verified]` An external load balancer serves the web portal and an internal one
serves in-VPC callers. A listener rule on the external load balancer routes the `/res/*` API paths to a
backend Lambda function. The internal load balancer has no `/res/*` rule; calls to the internal name
return 404.

**Desktops.** `[verified]` A virtual desktop is an EC2 instance launched on demand from a stock vendor
AMI and configured at first boot (§5). No RES-built AMI is involved unless an operator bakes one.

**Lambda functions.** `[from source]` Besides the API function, the tree defines:

- a proxy for the API
- two functions covering Cognito synchronization and Cognito triggers
- a DynamoDB table stream subscriber
- a bastion-host cleanup function
- a solution-metrics reporter
- the custom resources used during deployment

`[verified]` 2026.09 also runs an event-queue handler and a scheduled-event handler.

## 2. Code layout and runtime modules

`[verified]` The runtime is divided into **modules**: cluster manager, virtual desktop, bastion host,
connection gateway, and the installation scripts. A module is a unit that is built, packaged and deployed.
2026.06 adds a virtual desktop controller module (§7, §8).

`[verified]` The code is divided into **three layers**: the API layer at `source/idea/backend/`, the
service library at `source/idea/library/`, and the generated data model at `source/idea/data-model/`. The
library is used by Lambda functions, infrastructure hosts and container tasks.

These are two different divisions of the same system. `docs/develop/code-conventions.md` §1 to §3 hold the
rules for what belongs in each layer, the Smithy models as the API contract, and which code from the two
predecessor projects is still in use and where.

`[verified]` The tree contains the current library and data model at `source/idea/library/` and
`source/idea/data-model/`, and their predecessors at `source/idea/idea-sdk/` and
`source/idea/idea-data-model/`.

## 3. Where state is kept

`[from source]` The DynamoDB tables, each name prefixed with the environment name:

| Group | Tables |
|---|---|
| Configuration | `cluster-settings`, `modules` |
| Accounts and directory | `accounts.users`, `accounts.groups`, `accounts.group-members`, `accounts.sso-state`, `ad-automation`, `ad-sync.status` |
| Authorization | `authz.roles`, `authz.role-assignments`, `projects` |
| Virtual desktops | `vdc.controller.user-sessions`, `vdc.controller.user-sessions-counter`, `vdc.controller.software-stacks`, `vdc.controller.session-permissions`, `vdc.controller.permission-profiles`, `vdc.controller.schedules`, `vdc.controller.dcv-connection-tokens`, `vdc.controller.ssm-commands` |
| Coordination | `cluster-manager.distributed-lock`, `vdc.distributed-lock`, `ad-sync.distributed-lock` |
| Operations | `snapshots`, `apply-snapshot`, `email-templates` |

`[verified]` The `vdc.controller.*` names are present on 2026.09, which has no controller host.

`[verified]` **`cluster-settings` holds the settings that components read, including the URIs from which a
host fetches its application and its installation scripts. Hosts read these values at boot.** A changed
value applies to a host launched after the change, not to a running one. `<module>.app_package_uri` and
`cluster.installation_scripts_uri` name locations from which a host downloads and runs code. Write access
to this table, and write access to those locations, therefore has the same effect as write access to the
software itself. The Developer workflow section of `docs/develop/deploying-from-source.md` covers the
same mechanism from the patching side.

`[verified]` The three distributed-lock tables hold coordination locks taken by running operations. A host
replaced mid-operation leaves its lock behind, and RES doesn't clear it automatically.

**State outside DynamoDB.** `[verified]` Secrets Manager holds the credentials for the directory
administrator and the directory service account. On a deployment with a custom domain it also holds the
virtual-desktop certificate and its private key. EFS holds home directories, and an operator can onboard
additional filesystems after deployment. The staging bucket holds what hosts download at boot (§5).
Cognito holds portal identities and Active Directory holds POSIX identities (§4).

## 4. Identity

`[verified]` A deployment uses two identity systems, and a user can exist in one without existing in the
other.

- **Cognito** authenticates to the web portal. The administrator account created at deploy time,
  `clusteradmin`, is a Cognito user with no directory identity.
- **Active Directory** provides POSIX identity on hosts. Desktops resolve users and groups through the
  directory.

`[verified]` **Three compiled Go modules connect them**: `libnss_cognito`, `pam_cognito` and
`ssh_keygen`. The build produces them as shared objects and publishes them to the staging bucket, and
every host installs them at first boot. For `getent passwd <a directory user>` to resolve on a desktop,
`libnss_cognito` must have been fetched, installed, loaded by NSS, and be querying the directory.

`[verified]` **AD sync** is a container task that reads the directory and populates `accounts.users`,
`accounts.groups` and `accounts.group-members`. It takes `ad-sync.distributed-lock` while running. On the
verification runs it imported five users and three groups with their directory GIDs.

`[verified]` **Authorization is separate from both.** Project membership is a row in
`authz.role-assignments` binding an actor to a resource with a role. Updating a project with a `users`
list returns success and doesn't create membership. A newly deployed environment has no projects, ships
all software stacks attached to no project, and has no project membership for the administrator.
`docs/reference/first-run.md` has the sequence that resolves this.

## 5. The host boot sequence

`[verified]` Every host, infrastructure or desktop, is configured from nothing at first boot, in this
order:

1. Userdata runs and creates `/root/bootstrap`, writing `infra.cfg` and, where a proxy is configured,
   `proxy.cfg`.
2. Installation scripts are downloaded from the staging bucket, at a location read from
   `cluster-settings`.
3. Each completed phase writes a lock under `/root/bootstrap/semaphore/`.
4. The three host modules are downloaded from `host_modules/<module>/latest/<arch>/` in the staging
   bucket and installed into the operating system's PAM and NSS directories.
5. The application package is downloaded from the URI in `cluster-settings` for that module and unpacked
   under `/opt/idea/app/`.
6. `supervisord` starts the application, with one program definition naming the module.
7. On a desktop, DCV is configured and a session is created.

`[verified]` Three properties of this sequence:

- The host-module prefix contains no version segment, and the staging bucket name is fixed per account and
  region. Every environment in one account and region therefore reads the same host modules.
- The CloudWatch agent does not collect `/root/bootstrap/logs/`. Those logs exist only on the instance.
- The sequence runs in full on every launch.

## 6. The desktop launch sequence

`[verified]` On 2026.09:

1. The portal calls the API through the external load balancer's `/res/*` rule, which reaches a Lambda
   function.
2. Authorization resolves the caller against `authz.role-assignments` for the requested project. A caller
   who is not a project member is refused here.
3. The software stack is read from `vdc.controller.software-stacks`, which supplies the AMI, the
   architecture, and the constraints on instance type and volume size.
4. Provisioning runs through EC2 Fleet. The session record carries a `fleet_id` alongside an
   `instance_id`.
5. The instance boots and configures itself as in §5, including installing the host modules and joining
   the directory.
6. DCV starts and a session is created. A validation attempt counter is kept in
   `vdc.controller.user-sessions-counter` and doesn't reset on stop or start.
7. The session reaches `READY`. On the verification runs this took about eleven minutes from request.
8. A connection token is issued and recorded in `vdc.controller.dcv-connection-tokens`, and the connection
   gateway routes the session to the instance's private address.

`docs/operate/diagnosing-failures.md` is organized against this sequence.

## 7. Differences between 2026.06 and 2026.09

`[verified]` Three differences change where things are:

- 2026.06 runs three long-lived hosts, adding `vdc-controller`. 2026.09 runs two, and the API is served by
  a Lambda function.
- 2026.09 provisions desktops through EC2 Fleet. 2026.06 launches instances directly.
- Twelve of nineteen `/res/` API paths were renamed in 2026.09, and one operation changed from single to
  batch.

`docs/operate/upgrading-to-2026.09.md` has the full API path mapping and the behavioral difference in the
batch operation.

## 8. Components named in other documentation that are not present

`[verified]` Documentation a reader may find names three components, and none is present in 2026.09:

| Component | State |
|---|---|
| DCV session manager broker | Not present in 2026.06 or 2026.09. No broker log group, no session-manager-agent directory on a desktop, no broker service |
| `vdc-controller` host | Present in 2026.06, absent in 2026.09. The `vdc.controller.*` table names remain (§3) |
| OpenSearch | Present in neither tree. Older material may refer to it |
