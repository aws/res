# Upgrading to RES 2026.09

> **Note.** This document was written with AI assistance and is not part of the AWS documentation for RES. Treat it as directional: verify anything you depend on against the source tree and your own deployment.

2026.09 is the final RES release. It removes a host type, renames most of the virtual-desktop API paths,
and moves session provisioning onto EC2 Fleet.

**Markers.** Items marked `[verified]` were observed on a 2026.09 deployment built and run for the
purpose. Items marked `[from source]` were read from the code and not exercised. Items marked
`[inferred]` are unverified reasoning.

## Scope

This page covers the difference between 2026.06 and 2026.09, in the order it matters:

- **§1 to §3:** what breaks something you have built against RES.
- **§4 and §5:** what changed without breaking the upgrade.
- **§6:** what did not change.
- **§7:** the work all of it creates.

Every deployment behind this page was a fresh install.

**Converting a running environment in place is not covered here, because it isn't a documented or
supported path.** Upgrading means deploying a new environment. `ROADMAP.md` records in-place upgrade
as one of the capabilities RES was scoped not to do. Nothing on this page tells you what happens to
existing desktop sessions, because no deployment behind it had any.

---

## 1. Breaking: most virtual-desktop API paths were renamed

`[verified]` If you call the RES API directly from a script, a portal of your own, or any integration,
the renames are breaking changes. Twelve of nineteen paths under `/res/` were renamed, and the table
below is the complete mapping. The pattern is consistent: singular resource names became plural, and path
parameters moved from camelCase to snake_case. Review any direct API caller against it.

| 2026.06 | 2026.09 |
|---|---|
| `/res/virtual-desktop/session` | `/res/virtual-desktop/sessions` |
| `/res/virtual-desktop/session/{resSessionId}` | `/res/virtual-desktop/sessions/{res_session_id}` |
| `/res/virtual-desktop/session-permission` | `/res/virtual-desktop/session-permissions` |
| `/res/virtual-desktop/software-stack` | `/res/virtual-desktop/software-stacks` |
| `/res/virtual-desktop/software-stack/{stackId}` | `/res/virtual-desktop/software-stacks/{stack_id}` |
| `/res/virtual-desktop/software-stack/create-from-session` | `/res/virtual-desktop/software-stacks/create-from-session` |
| `/res/virtual-desktop/permission-profile` | `/res/virtual-desktop/permission-profiles` |
| `/res/virtual-desktop/permission-profile/{profileId}` | `/res/virtual-desktop/permission-profiles/{profile_id}` |
| `/res/virtual-desktop-utils/allowed-instance-type` | `/res/virtual-desktop-utils/allowed-instance-types` |
| `/res/virtual-desktop-utils/allowed-instance-type-for-session` | `/res/virtual-desktop-utils/allowed-instance-types-for-session` |
| `/res/virtual-desktop-utils/permission-profile` | `/res/virtual-desktop-utils/permission-profiles` |
| `/res/virtual-desktop-utils/permission-profile/{profileId}` | `/res/virtual-desktop-utils/permission-profiles/{profile_id}` |

Seven paths are unchanged: `session-connections`, `session-screenshots`, `shared-permissions`, and
`sessions/delete`, `sessions/reboot`, `sessions/start`, `sessions/stop`.

**No endpoint was removed.** Both releases expose 26 operations. The `[Tear Down]` commits in the
release history removed *internal* event handlers and controller services, not public endpoints.

### The one operation that changed shape

`[verified]` `create_session` is gone, replaced by `batch_create_session`. Same path family, different
contract:

- The request takes a `sessions` **array** rather than one session.
- The response is **HTTP 200 even when a session fails**, returning `successful_list` and
  `unsuccessful_list`. Each failed entry carries an `error_code` and a `message`.

Per-session failures now arrive inside a 200, so a client that treats HTTP 200 as success will believe
it launched desktops it didn't launch. **Check `unsuccessful_list`.**

Example of a failure that returns 200:

```json
{"successful_list": [],
 "unsuccessful_list": [{"error_code": "BadRequestException",
                        "message": "User clusteradmin does not belong in the selected project.",
                        "session": {"...": "..."}}]}
```

## 2. The vdc-controller host is gone

`[verified]` 2026.06 ran three infrastructure hosts; 2026.09 runs **two**. `cluster-manager` and
`vdc-gateway` remain. The virtual-desktop-controller host is removed and its work moved into Lambda
functions. The API is served by `<env>-backend-lambda` behind an ALB rule on `/res/*`, and event
handling moved to a set of Lambdas including `<env>-vdc-events-queue-handler` and a scheduled-event
function.

What this changes for you:

- **Cost and footprint drop** by one instance per environment.
- **Where you look for logs changes.** Anything you had pointed at the vdc-controller host, whether SSH,
  log tailing or a dashboard widget, has no target. Application logs for the API are now in the Lambda's
  CloudWatch log group rather than on a host.
- `[from source]` The `tests.virtual-desktop-controller` tox environment was removed with it, so the
  unit-test suite count drops from ten to nine.

## 3. Desktops now provision through EC2 Fleet

`[verified]` A launched session's server record has a `fleet_id` alongside `instance_id`, where
previously desktops were plain RunInstances calls.

What this changes for you:

- `[from source]` Cleanup changed to match. `deletion_cleanup_resources_lambda` now deletes Fleets and
  Launch Templates as well as instances. The new calls are `delete_fleets` with
  `TerminateInstances=True`, in `_delete_fleets`, and `delete_launch_template`. Neither exists in
  2026.06.
- `[inferred]` Any automation of your own that finds RES desktops by tag or by describing instances
  should still work, because the instances are ordinary EC2 instances. Automation that assumed no Fleet
  or Launch Template resources exist in the account may need adjusting. Not exercised.

## 4. Software stacks and AMIs

`[verified]` The pinned AMI tables were refreshed for this release. On a fresh 2026.09 install in
us-west-2 the six base stacks resolve to the 2026-08-03 Amazon Linux image set, RHEL **9.8.0** (up from
9.7.0), and current Ubuntu and Windows images. None is past its vendor deprecation date; the earliest
expiry is 2026-11-01.

`[verified]` **A `ubuntu2404` base software stack is new** in this release.

**2026.09 is the last AWS refresh of these tables.** AMI pins are release-time values: maintain your own
mapping and check `DeprecationTime` on the entries you rely on. A deprecated AMI still launches; a
deregistered one doesn't. The pinned tables are `region_ami_config.yml` and
`base-software-stack-config.yaml`, both under `source/idea/infrastructure/resources/config/`.

## 5. Fixes in this release

| Symptom | Change |
|---|---|
| Desktops stuck in `STOPPING`, never reaching `Stopped` (public issue #183) | `[from source]` The VDI helper Lambda's memory was raised from 128 MB to 512 MB. The commit names an EC2 API timeout on idle stop as the cause |
| Ubuntu 22.04 desktops failing to bootstrap since GitHub's SHA-1 TLS sunset | `[from source]` `git` is forced to HTTP/1.1 during bootstrap. Also present on the 2026.06 patch branch |
| AMI baking failing with an unset `HOME` | `[from source]` `HOME` is exported before `git config` |
| The portal's launch form refusing to submit with no error | `[verified]` Submitting works. The form now posts the batch shape |

## 6. What did *not* change

- `[verified]` The install template remains at **38 parameters, none with a default**.
- `[verified]` The `node_version: 18.18.0` pin in `software_versions.yml` has not moved, and the
  committed `yarn.lock` still resolves `nth-check` to 3.0.1, so building the web portal from source
  needs Node ≥ 20.19.0. Raise the pin before you build. See `docs/develop/deploying-from-source.md`.
- `[verified]` A fresh install still has **zero projects**, all base software stacks still arrive with
  `projects: []`, and the administrator is still not a member of any project. See
  `docs/reference/first-run.md`.
- `[verified]` The desktop launch form opens at a storage size of 10 GB, below every stack's 50 GB
  minimum. Selecting a stack and instance type raises it automatically, so it's misleading rather than
  blocking.
- `[from source]` The ad-sync container image default is unchanged, and still points at a 2023-era image
  that contains no ad-sync application. Supply your own registry value.
- `[verified]` The staging bucket is still fixed at `res-staging-<region>-<account>` and the host-module
  prefix is still unversioned, so **two environments in one account and region share host modules**.
  Deploying a second environment at a different version changes what the first one loads at host boot.

## 7. Upgrade checklist

This is the work the changes above create. It assumes you are standing up 2026.09, not converting a
running 2026.06 environment in place.

1. **Inventory your API callers** and apply the path renames in §1.
2. **Handle `unsuccessful_list`** anywhere you create sessions, because failures now arrive inside a
   200. Read `error_code` and `message` on each failed entry.
3. **Remove any dependency on the vdc-controller host**: dashboards, log paths, SSH targets, runbooks.
4. `[inferred]` **Expect Fleet and Launch Template resources** in the account and allow for them in any
   IAM policy or cleanup automation of your own. Not exercised; confirm in a test environment.
5. **Take ownership of the AMI tables** before the pins age out. This release is the last refresh.
6. **If you build from source**, raise the Node pin first. Otherwise the build fails at the portal step.
7. **Supply your own ad-sync registry value.** Per §6, the default points at a 2023-era image that
   contains no ad-sync application.
8. **Run one environment per account and region.** Per §6, two environments in one account and region
   share host modules, and deploying the second at a different version changes what the first one loads
   at host boot.

For failures during or after the upgrade, see `docs/operate/diagnosing-failures.md`.
