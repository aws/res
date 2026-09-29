# First run

> **Note.** This document was written with AI assistance and is not part of the AWS documentation for RES. Treat it as directional: verify anything you depend on against the source tree and your own deployment.

What an administrator must do between "the CloudFormation stack reached `CREATE_COMPLETE`" and "a
user can launch a virtual desktop".

A new RES environment needs three setup steps before anyone can launch a desktop: create a project,
attach software stacks to it, and add the administrator to the project as a user. A fresh install has no
projects, no stack attached to anything, and an administrator with no project access. This page covers
that setup, plus the install parameters that are easy to get wrong.

Everything below was confirmed against a running RES 2026.06 environment built entirely from public
source. Claims marked `[verified on 2026.09]` were confirmed the same way, on a 2026.09 environment
instead. Claims taken from source rather than from a running environment are marked `[from source]`.
Claims that are neither are marked `[inferred]`.

> **Support status.** RES is supported by AWS until the End of Support Life of the 2026.09 release.
> After that no version falls under the support policy. See `SUPPORT.md`.

---

## 1. Before you install

RES does not create its own identity provider, directory or shared filesystem. Three things must
exist before the install stack runs:

| Prerequisite | What RES needs from it | Install parameters that consume it |
|---|---|---|
| Active Directory | An LDAP-reachable AD with a service account, and OUs for users, groups and computers | `ActiveDirectoryName`, `ADShortName`, `LDAPBase`, `LDAPConnectionURI`, `UsersOU`, `GroupsOU`, `ComputersOU`, `SudoersGroupName`, `ServiceAccountUserDN`, `ServiceAccountCredentialsSecretArn` |
| Amazon Cognito user pool | Web portal and API authentication | `CognitoUserPoolId`, `CognitoUserPoolDomainUrl`, or leave both empty and RES creates a pool (see §2.3) |
| Shared home filesystem | Mounted on every VDI as `/home` | `SharedHomeFileSystemId` |

You also need a VPC with at least two Availability Zones. Infrastructure hosts and VDI take private
subnets. The load balancer takes its own subnets, and those subnets must be public if the load balancer
is internet-facing.

### Evaluation shortcut

The `samples/batteries-included/` set in this repository stands up a VPC, an AWS Managed Microsoft AD
populated with demo users and groups, and an EFS filesystem, as one nested CloudFormation stack. It
emits the outputs the RES install parameters need.

Two things to know about it:

- **It is demo-grade.** It seeds a directory with fixed sample users, uses passwords you supply as
  stack parameters, and makes no attempt at directory hardening, backup or multi-account layout. Use
  it to evaluate RES, not as the identity foundation for a production deployment.
- `CreateActiveDirectory` **defaults to `False`.** Left alone, the stack creates no directory at all
  and RES has nothing to bind to. Set it to `True`.

AWS Managed Microsoft AD provisioning takes the longest part of that stack, roughly 20 to 40 minutes.

---

## 2. The 38 parameters

The install template declares 38 parameters and **not one has a `Default`**. Verified by reading
the `Parameters` block of the deployed template: 38 entries, zero with a `Default` key.

The consequence depends on how you deploy:

- **Console.** Every field renders blank. 28 of the 38 are labeled `- Optional` in their parameter
  label, and can be left blank.
- **CLI or SDK.** CloudFormation rejects `create-stack` unless every parameter without a default is
  supplied. You must pass all 38 explicitly, including the ones you want empty:

  ```
  ParameterKey=HttpProxy,ParameterValue=
  ```

  Omitting them produces `Parameters: [...] must have values`, listing whichever you missed.

The authoritative and always-current parameter table is
`source/idea/infrastructure/install/parameters/`. This page groups the parameters rather than
transcribing them.

### 2.1 Required: 10 parameters

These are the ten that are *not* labeled `- Optional`. Derived by taking the 38 template parameters
and subtracting those whose label ends in `- Optional`, from
`idea.infrastructure.install.constants`.

| Parameter | Note |
|---|---|
| `EnvironmentName` | Must match `res-[a-z_0-9-]{0,7}`, so at most 11 characters including the prefix. Appears in the name of nearly every resource RES creates, including the DynamoDB table prefix. Choose deliberately; it can't be changed later. |
| `VpcId` | |
| `LoadBalancerSubnets` | At least two, different AZs. Must be public if `IsLoadBalancerInternetFacing` is `true`. |
| `InfrastructureHostSubnets` | At least two private, different AZs. |
| `VdiSubnets` | At least two private, different AZs. |
| `SSHKeyPair` | An existing EC2 key pair name. |
| `SharedHomeFileSystemId` | Pattern is `fs-[0-9a-f]{17}`, with no empty option. |
| `IsLoadBalancerInternetFacing` | Allowed values are `true` and `false` only. Unlike the other two booleans, empty is **not** accepted. |
| `ClientIp` | A CIDR, pattern-enforced. It is the network access control on the portal and the bastion host. With a public certificate and public DNS the portal is reachable from the internet. |
| `AdministratorEmail` | Not labeled optional, but its pattern does admit the empty string. `[inferred]` Supplying it is the intent; whether an empty value degrades anything beyond notification delivery is unconfirmed. |

### 2.2 Optional, but empty means something specific

These are labeled `- Optional`, but leaving one blank still selects a behavior.

**Cognito user pool: `CognitoUserPoolId`, `CognitoUserPoolDomainUrl`.** See §2.3.

**Active Directory: the ten directory parameters listed in §1.** Labeled optional, but RES
authenticates VDI users against a directory through PAM and NSS host modules. `[inferred]` Treat them as required unless you have established otherwise for your own deployment.

**`DisableADJoin`, `EnableLdapIDMapping`.** Both accept `True`, `False` or empty. `[from source]`
`EnableLdapIDMapping` set to `False` makes RES use the `uidNumber` and `gidNumber` attributes from
your directory; `True` makes RES map IDs itself. `DisableADJoin` set to `True` stops Linux and
Windows hosts from joining the domain automatically. Note that Windows instances need a domain join
to launch, so with this set you must supply your own join logic.

**Custom domain: `CustomDomainNameforWebApp`, `ACMCertificateARNforWebApp`,
`CustomDomainNameforVDI`, `CertificateSecretARNforVDI`, `PrivateKeySecretARNforVDI`.** These come in
two pairs plus a name. The two legs are asymmetric, and that drives what kind of certificate you need:

- The **web app** takes an ACM certificate ARN. The ALB terminates TLS.
- The **VDI** leg takes the certificate *and its private key* as Secrets Manager ARNs, because the
  DCV connection gateway terminates TLS itself. ACM never releases a private key, so an
  ACM-issued certificate cannot serve this leg. You need a certificate you hold the key for.

One certificate that covers both `<domain>` and `*.<domain>` can serve both legs. Import it into ACM
for the web app, and store the same certificate and its key in Secrets Manager for VDI. That is how the
reference environment was configured.

**`IAMPermissionBoundary`.** RES attaches the boundary you name to every IAM role it creates, at
creation time, so nothing has to be attached afterwards and there is no race against instance launch.
The reference environment used it to deny the deployment access to several AWS-owned buckets and
registries for the duration of the install.

**`InfrastructureHostAMI`.** Empty means RES picks a stock AMI for your region from
`source/idea/infrastructure/resources/config/region_ami_config.yml`. AL2, RHEL 8 and RHEL 9 are the
supported alternatives.

### 2.3 `CognitoUserPoolId` is emptyable on purpose

The behavior:

| `CognitoUserPoolId` | Result |
|---|---|
| Empty | RES creates a new Cognito user pool and its domain, and ignores `CognitoUserPoolDomainUrl`. |
| A pool ID | RES adopts that pool. `CognitoUserPoolDomainUrl` then becomes mandatory in practice. |

This is deliberate. Two RES environments can share one identity pool, which is what makes a blue/green
RES deployment possible:

1. Stand up the new environment against the existing pool.
2. Cut over to it.
3. Retire the old environment.

Users keep their identities and credentials throughout.

Record this in your runbook. A parameter with no default that the console marks optional, whose empty
value changes what infrastructure gets created, looks like a bug. `[from source]` The template's own
parameter description does say "RES will create one by default if no Cognito user pool is specified".
The prerequisites stack emits no Cognito outputs, so a deployer wiring outputs to parameters finds
nothing to wire here and assumes something is missing.

### 2.4 Boolean casing is inconsistent

Verified from the deployed template's `AllowedValues`:

| Parameter | Accepted values |
|---|---|
| `DisableADJoin` | `True`, `False`, `` |
| `EnableLdapIDMapping` | `True`, `False`, `` |
| `IsLoadBalancerInternetFacing` | `true`, `false` |

Two capitalized, one lowercase, and the lowercase one is the only one of the three that doesn't
accept empty. The CloudFormation error is `Parameter 'X' must be one of AllowedValues` with the
allowed list attached but no indication which casing convention applies, so you find out by
submitting and reading the rejection.

---

## 3. Getting the install template

The install template is a single CloudFormation stack. Two ways to get it:

- **Synthesize it yourself.** `cdk synth ResearchAndEngineeringStudio` with the `publish_templates`
  context key unset. This produces a template whose asset references point at a staging bucket in
  your own account, and which contains no reference to any AWS-owned distribution bucket. This is the
  path a self-supporting operator should use; see `docs/reference/external-dependencies.md`.
- **Use a published template**, while the AWS-owned regional buckets remain readable. Also covered in
  `docs/reference/external-dependencies.md`, including when that stops being an option.

---

## 4. After the stack completes: three required steps

Nothing in the product prompts you through this. Sign in to the portal as `clusteradmin` and do these
three things, in this order. Until you finish all three, the desktop launch dialog cannot produce a
working session.

### Step 1: create a project

A fresh install has **zero** projects. Verified: the `<env-name>.projects` DynamoDB table on a
freshly installed environment is empty, and the launch dialog's Project list is therefore empty with
no indication of why.

1. In the portal, go to **Environment management → Projects** (`#/cluster/projects`).
2. Choose **Create project**.
3. Fill in **Title**, **Project ID** (`name`), **Description**, and **Allowed sessions per user**.
4. Under **Team Configurations**, use **Add user** to add `clusteradmin` with role **Project
   Member**. This is Step 3 below; doing it here saves a second pass.
5. Submit.

By API:

```
POST https://<portal-domain>/cluster-manager/api/v1/Projects.CreateProject
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "header": { "namespace": "Projects.CreateProject", "request_id": "<uuid>" },
  "payload": {
    "project": {
      "name": "my-project",
      "title": "My Project",
      "description": "...",
      "enable_budgets": false,
      "allowed_sessions_per_user": 5
    }
  }
}
```

`[from source]` The request envelope and endpoint path are read from the portal's own API client;
the namespace is appended to the context path, so the URL ends in the namespace.

### Step 2: attach each software stack to the project

RES ships six base software stacks. On 2026.09, verified live: AL2023 x86_64 and arm64, Ubuntu 22.04,
Ubuntu 24.04 (**new in 2026.09**), RHEL 9 and Windows. **All arrive with `projects: []`**, so none appears
in any project's launch dialog until you attach it. There is no bulk operation, so each stack is edited
individually.

Verified: on a freshly installed environment all six rows in
`<env-name>.vdc.controller.software-stacks` had an empty `projects` list. After the reference run
attached one stack to one project, that stack's list held one project ID and the other five were
still empty.

The six, and the operating system each installs:

| Stack ID | OS |
|---|---|
| `ss-base-amzn2023-x86-64-base` | Amazon Linux 2023, x86-64 |
| `ss-base-amzn2023-arm64-base` | Amazon Linux 2023, arm64 |
| `ss-base-rhel9-x86-64-base` | Red Hat Enterprise Linux 9, x86-64 |
| `ss-base-ubuntu2204-x86-64-base` | Ubuntu 22.04, x86-64 |
| `ss-base-ubuntu2404-x86-64-base` | Ubuntu 24.04, x86-64 |
| `ss-base-windows-x86-64-base` | Windows Server 2022, x86-64 |

1. Go to **Session management → Software stacks** (`#/virtual-desktop/software-stacks`).
2. Select a stack, choose **Edit**.
3. Add your project to **Projects**, and save.
4. Repeat for every stack you want available. Attach only the ones you intend to offer: an unattached
   stack is invisible, which is one way to restrict a project to a single OS.

By API:

```
PUT https://<portal-domain>/res/virtual-desktop/software-stack/<stack-id>
Authorization: Bearer <access-token>
Content-Type: application/json

{ "software_stack": { ...the stack as returned by GET, with the project ID added to "projects"... } }
```

`[from source]` Route and method read from the generated API client. Send the whole software stack
object back, not a patch.

### Step 3: add the administrator as an individual project user

Attaching a project to the `RESAdministrators` directory group does **not** give `clusteradmin`
access to it. Add the administrator to the project as an individual **user**.

Attaching the admin group looks like it should work, and the portal gives no error when it does not.
The mechanism, verified end to end on the reference environment:

1. `clusteradmin` is created by RES as a **native Cognito user**, not a directory user. Verified: its
   row in `<env-name>.accounts.users` has `identity_source` `Native user` and
   `additional_groups: []`. It's in no group, and no directory sync will ever put it in one.
2. The `<env-name>.accounts.group-members` table is **empty** on a fresh install, 0 items, verified,
   even though AD sync had imported 5 users and 3 groups including `RESAdministrators` with its GID.
3. Group membership is materialized into `group-members` by the user-activation path, which runs on a
   user's **first successful single-sign-on**. `[from source]` Directory users are created by AD sync
   with `is_active: false`; the portal's SSO callback activates a user on first sign-in, and
   activation is what copies `additional_groups` into `group-members`.
4. On a fresh install, `identity-provider.cognito.sso_enabled` is `false`, verified in
   `<env-name>.cluster-settings`, so no directory user can sign in, so nobody is ever activated,
   so `group-members` stays empty.

Net effect: a group-scoped role assignment on a fresh install resolves to nobody. Verified: the
reference environment's `<env-name>.authz.role-assignments` table held both a `group` assignment for
`RESAdministrators` and a `user` assignment for `clusteradmin` on the same project, and only the user
assignment did anything.

Via the portal, in the project's **Team Configurations** section, choose **Add user**, select
`clusteradmin`, and set the role to **Project Member**. (The only two roles are `project_member` and
`project_owner`, verified from `<env-name>.authz.roles`.)

**Do not try to do this with `Projects.UpdateProject`.** `[verified on 2026.09]` That call accepts a
`users` array in its payload, returns `success: true`, and **silently does nothing**. The project it
returns has no users, and a subsequent launch still fails with `User <name> does not belong in the
selected project.` Membership is governed only by role assignments.

By API:

```
POST https://<portal-domain>/cluster-manager/api/v1/Authz.BatchPutRoleAssignment
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "header": { "namespace": "Authz.BatchPutRoleAssignment", "request_id": "<uuid>" },
  "payload": {
    "items": [{
      "request_id":    "<uuid>",
      "resource_id":   "<project-id>",
      "resource_type": "project",
      "actor_id":      "clusteradmin",
      "actor_type":    "user",
      "role_id":       "project_member"
    }]
  }
}
```

Once SSO is configured and directory users have signed in at least once, group assignments start
working normally and can manage access at scale.

### A side effect of project membership

The portal's own navigation is gated on project membership. `[from source]` The extra "Environment
Management → Projects" section that non-admin users see is only rendered when the signed-in user
belongs to at least one project. Administrators reach Projects through the admin navigation regardless,
so this does not block Step 1. A non-admin user who belongs to no project sees a portal with almost
nothing in it. That is the expected state.

---

## 5. Launching the first desktop

With all three steps done, **Desktops → My virtual desktops → Launch new virtual desktop** should
offer your project and the stacks you attached.

What to expect on the form:

- `[verified on 2026.09]` **The Software Stack dropdown shows only stacks attached to the selected
  project**, so if it looks empty or short, Step 2 is incomplete rather than the list being broken.
- `[verified on 2026.09]` **The form does submit.** On 2026.06 it refused silently on every attempt,
  issuing no request and showing no error, which forced desktop creation through the API. That is fixed.
  A submission can still stop at the form's own validation, which is a different case, described below.
- `[verified on 2026.09]` **Storage Size (GB) opens at 10, below every stack's 50 GB minimum.**
  Selecting a software stack and an instance type, both mandatory before the form can be submitted,
  raises the field to the stack's minimum, so the value corrects itself in the normal flow. Observed
  going from `10` to `50`, and the created session had 50 GB. If you submit without changing instance
  type, the API rejects it:

  ```
  root volume size: 10.0 is less than the minimum required root volume size: 50.0
  when hibernation is disabled
  ```

  With hibernation enabled the minimum rises by the instance's RAM. Set Storage Size to at least 50
  before submitting.

Two further problems on the launch path, both observed on the reference environment:

- **The form can refuse to submit while showing only its generic helper text**, issuing no create
  request at all. This is not the 2026.06 submission bug above, which is fixed: here the form shows its
  validation helper text and stops. If that happens, the API path works cleanly once you know the
  payload shape.
- **Schema validation and application validation disagree about field names.** The JSON-schema layer
  wants a nested `session.software_stack` object; the application layer then wants a flat
  `session.software_stack_id` plus `session.base_os`. A direct API caller has to supply both shapes,
  and errors surface one requirement at a time, so the accepted payload is found by iteration.

---

## 6. Confirming it worked

On a Linux VDI that has reached `READY`, these five checks together establish that the whole chain
is functioning. DCV is serving, and the host is resolving directory identities through the RES host
modules rather than out of `/etc/passwd`:

```
systemctl is-active dcvserver     → active
systemctl is-active supervisord   → active
dcv list-sessions                 → Session: 'console' (owner:<user> type:console)
getent passwd <user>              → <user>:x:<uid>:<gid>::/home/<user>:/bin/bash
id <user>                         → uid=<uid>(<user>) gid=<gid> groups=<gid>
```

The UID and GID are the part to check. If they fall in your directory's ID-mapping range rather
than the local range, the answer came from the directory through `libnss_cognito`, which means the
NSS module was fetched, installed and loaded successfully. A user that resolves out of `/etc/passwd`
looks the same to `getent` and isn't the same thing.

`supervisord` being active is also a negative check on a known bootstrap failure mode: when a
third-party download during VDI bootstrap fails, `supervisord` is typically what never starts. See
`docs/reference/external-dependencies.md`.
