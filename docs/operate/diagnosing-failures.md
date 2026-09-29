# Diagnosing failures

> **Note.** This document was written with AI assistance and is not part of the AWS documentation for RES. Treat it as directional: verify anything you depend on against the source tree and your own deployment.

Claims carry a mark saying how they were established. Do not remove the marks without checking the
claim.

- `[verified]` was confirmed on a running RES deployment (Amazon Linux 2023 infrastructure hosts,
  `us-west-2`).
- `[verified on 2026.09]` was confirmed on a running 2026.09 deployment.
- `[verified method]` is a procedure that was run and found to work.
- `[verified correction]` corrects a statement made elsewhere, and the correction was confirmed on a
  running deployment.
- `[from source]` was read out of the source tree rather than observed on a deployment.
- `[inferred]` was derived by reasoning rather than confirmed.
- `[unverified]` was not re-verified on a running deployment. Treat it as a strong prior rather than
  a confirmed fact.

**Which release this describes.** Most of it was verified on **2026.06**, then re-checked against a
running **2026.09** deployment. Where the two differ, the difference is called out inline. Three
differences change how you diagnose, so they are stated up front:

- **There is no VDC controller host in 2026.09.** 2026.06 ran three infrastructure hosts; 2026.09 runs
  two, `cluster-manager` and `vdc-gateway`. The API moved into `<env>-backend-lambda`, so API-layer logs
  are in that Lambda's CloudWatch log group, not on a host. Anything below that tells you to look on the
  VDC controller applies to 2026.06 only.
- **Desktops provision through EC2 Fleet in 2026.09**, so a session record has a `fleet_id` as well
  as an `instance_id`, and a failure can now sit in Fleet rather than in RES.
- **The VDI helper Lambda was raised from 128 MB to 512 MB in 2026.09**, which changes the first thing
  to check for desktops stuck in `STOPPING`. See the `STOPPING` row in §1.5.

[`../operate/upgrading-to-2026.09.md`](../operate/upgrading-to-2026.09.md) covers the same 2026.09
differences.

## Scope

RES failures are rarely reported at the layer where they happen. A user sees "the desktop is
stuck", an administrator sees an instance in `ERROR`, and the cause is several layers down and often
not in RES at all. This document records which symptoms map to which causes, in what order to look,
and how to tell a RES defect from a misconfiguration of the environment RES was deployed into.

What each section holds. §1 identifies the failure class from what you can see, ranked by how often
each class recurred. §2 eliminates the causes that are not RES, which is where half of all recorded
failures ended up, and §2.4 is the triage sequence to run before investigating anything as a RES
defect. §3 says which log answers which question. §4 is the reconstruction ladder, for a desktop
failure that survives all of the above. §5 is a symptom catalogue, which is the fastest route if your
symptom is already in it.

It does not teach you the tools: it assumes you can read a log, query CloudWatch Logs Insights, and
open an SSM session to an instance. Four adjacent subjects are documented elsewhere. Applying a
patch, and recovering from one, is the Developer workflow section of
[`../develop/deploying-from-source.md`](../develop/deploying-from-source.md). Defects known in a given
release, with their workarounds, are the wiki page index and the issue list on GitHub; §5.1 has both.
A fresh environment that has never worked, rather than one that has stopped working, is
[`../reference/first-run.md`](../reference/first-run.md). The third-party artifacts a host fetches at
every boot, which are a recurring cause of bootstrap failure, are
[`../reference/external-dependencies.md`](../reference/external-dependencies.md).

## Start here

1. Search the known-issue sources (§5.1).
2. Run the triage sequence (§2.4).
3. Match your symptom: §5 first, then §1.
4. Read the log that answers your question (§3).
5. Reconstruct the desktop, one layer at a time (§4).

## Contents

- [1. Recurring failure modes](#1-recurring-failure-modes)
  - [1.1 Test and deployment-pipeline instability](#11-test-and-deployment-pipeline-instability)
  - [1.2 VDI bootstrap and provisioning failures](#12-vdi-bootstrap-and-provisioning-failures)
  - [1.3 Environment misconfiguration presenting as a RES defect](#13-environment-misconfiguration-presenting-as-a-res-defect)
  - [1.4 DCV integration defects](#14-dcv-integration-defects)
  - [1.5 Idle detection and auto-stop defects](#15-idle-detection-and-auto-stop-defects)
  - [1.6 Patch and release mechanics](#16-patch-and-release-mechanics)
  - [1.7 Scale and throughput limits](#17-scale-and-throughput-limits)
  - [1.8 Windows desktop failures on record](#18-windows-desktop-failures-on-record)
- [2. Failures that are not RES](#2-failures-that-are-not-res)
  - [2.1 Network](#21-network)
  - [2.2 Identity and AD](#22-identity-and-ad)
  - [2.3 Configurations that are outside what RES supports](#23-configurations-that-are-outside-what-res-supports)
  - [2.4 A cheap triage sequence](#24-a-cheap-triage-sequence)
- [3. Log locations, consolidated](#3-log-locations-consolidated)
  - [3.1 Infrastructure hosts](#31-infrastructure-hosts-cluster-manager-vdc-controller-connection-gateway)
  - [3.2 Linux virtual desktops](#32-linux-virtual-desktops)
  - [3.3 Windows virtual desktops](#33-windows-virtual-desktops)
  - [3.4 CloudWatch log groups](#34-cloudwatch-log-groups)
  - [3.5 Bootstrap logs are not centralized](#35-bootstrap-logs-are-not-centralized)
  - [3.6 Which log answers which question](#36-which-log-answers-which-question)
  - [3.7 Collecting a diagnostic bundle](#37-collecting-a-diagnostic-bundle)
- [4. The VDI failure isolation ladder](#4-the-vdi-failure-isolation-ladder)
  - [Rung 1. A bare instance from the same AMI](#rung-1-a-bare-instance-from-the-same-ami)
  - [Rung 2. The same AMI plus the RES desktop userdata](#rung-2-the-same-ami-plus-the-res-desktop-userdata)
  - [Rung 3. The same AMI plus the install scripts directly](#rung-3-the-same-ami-plus-the-install-scripts-directly)
  - [Rung 4. Bisect the configuration step](#rung-4-bisect-the-configuration-step)
  - [Rung 5. Bisect the install step](#rung-5-bisect-the-install-step)
  - [Notes on using the ladder](#notes-on-using-the-ladder)
- [5. Symptoms seen in the field](#5-symptoms-seen-in-the-field)
  - [5.1 Search the published known-issue sources before pattern-matching](#51-search-the-published-known-issue-sources-before-pattern-matching)
  - [5.2 Desktop lifecycle](#52-desktop-lifecycle)
  - [5.3 Connection failures](#53-connection-failures)
  - [5.4 Proxy handling differs between Windows and Linux](#54-proxy-handling-differs-between-windows-and-linux)
  - [5.5 Portal and API](#55-portal-and-api)
  - [5.6 Identity and directory](#56-identity-and-directory)
  - [5.7 Upgrade and installation](#57-upgrade-and-installation)
  - [5.8 AMI and image build](#58-ami-and-image-build)
  - [5.9 Infrastructure and performance](#59-infrastructure-and-performance)
  - [5.10 Windows desktops](#510-windows-desktops)
  - [5.11 Before you offer a fix](#511-before-you-offer-a-fix)
  - [5.12 Failure patterns in how these were diagnosed](#512-failure-patterns-in-how-these-were-diagnosed)
  - [5.13 DynamoDB tables worth knowing during diagnosis](#513-dynamodb-tables-worth-knowing-during-diagnosis)

---

## 1. Recurring failure modes

This section is organized by cause class, and §1.1 to §1.7 were verified. §5 covers the same ground
organized by observable symptom, and is unverified. Start with §5 if your symptom is concrete.

The classes below are ordered roughly by how often they recur in the field. Use the order as a search
order and start at the top. The ordering is a judgment, not a measurement: one incident often evidences
two classes.

Two things the order does not show. Environment misconfiguration (§1.3) is as common as pipeline
instability. A large share of failures turn out to be the network, directory, AMI or launch scripts of
the environment RES was deployed into, not RES. And patch and release mechanics (§1.6) recurs more often
than its position in the section order suggests.

| Class | How often |
|---|---|
| Test and deployment-pipeline instability (§1.1) | Most common |
| Environment misconfiguration presenting as a RES defect (§1.3) | Most common |
| VDI bootstrap and provisioning failures (§1.2) | Common |
| DCV integration defects (§1.4) | Common |
| Patch and release mechanics (§1.6) | Common |
| Idle detection and auto-stop defects (§1.5) | Less common |
| Scale and throughput limits (§1.7) | Least common |
| Windows desktop failures on record (§1.8) | Not ranked |

### 1.1 Test and deployment-pipeline instability

**What you observe.** Integration or smoke tests fail without a code change. A deployment of an
unchanged template fails in one region and succeeds in another. Reruns pass.

**What it usually is.** Almost never RES. The recorded causes, in rough order of frequency:

| Signature | Cause |
|---|---|
| `RunInstances` throttling, `Failed to fulfill capacity` | EC2 API rate limit or no capacity for the instance type in that AZ |
| Insufficient capacity for a GPU type (for example `g5.xlarge`) | Regional GPU capacity, worst for Windows plus NVIDIA stacks |
| `InvalidInstanceId`, "Instances not in a valid state for account" | Hibernate/resume raced the instance state machine |
| SSM command waiter timeout | SSM agent not yet ready, or the command was sent before the target service started |
| `apt` or `dnf` stalls during bootstrap | Upstream distribution mirror outage. Bootstrap has no retry or mirror fallback |
| Bootstrap fails on a host that launched fine yesterday | An SSM Patch Manager window installed packages while bootstrap was running |
| Browser-driven tests fail at the very end | Browser and browser-driver versions drifted apart in the build image |
| A test fails only in some regions | The test depends on a service or service tier not available in that region (FSx for ONTAP is the recorded example) |

**How to tell it apart from a real defect.** Three questions. Does it reproduce in a second
region? Does it reproduce on a rerun with no change? Is the failure inside a RES log or inside an
AWS API response? A failure that appears only in one region, clears on rerun, and shows an AWS API
error rather than a RES stack trace is environmental.

**The trap specific to RES.** Some of these were never fixed, only worked around. Several
integration tests were disabled rather than repaired, and at least one test mutates global state
(disabling a directory group) which poisons any other test running in parallel with it. If a suite
fails in a way that implicates authorization or project membership for a user that should be
fine, suspect test cross-talk before you suspect RES authorization.

### 1.2 VDI bootstrap and provisioning failures

**What you observe.** Nearly always one of two things: the desktop sits in `Provisioning` and then
moves to `Error`, or it reaches `Ready` and cannot be connected to or logged into. The state in the
portal tells you almost nothing about the cause.

VDI bootstrap runs in ordered phases and drops a lock file as each one completes. On a healthy
Linux desktop, `/root/bootstrap/semaphore/` contains, in completion order `[verified on 2026.09]`:

| Lock file | Means |
|---|---|
| `pre_install_finished.lock` | Userdata ran, the bootstrap bundle downloaded and unpacked |
| `custom_script.lock` | Any configured custom launch scripts ran |
| `install_finished.lock` | `install.sh` completed: packages, DCV, directory client |
| `install_post_reboot_finished.lock` | `install_post_reboot.sh` completed after the reboot |
| `app_installed.lock` | The RES desktop application payload is in place |
| `linux_vdi_config.lock` | Desktop configuration applied |
| `linux_vdi_config_host_ready.lock` | Host signalled ready |

`[verified on 2026.09]` Timestamps on a healthy desktop confirm that order, with one caveat.
`pre_install_finished.lock` and `custom_script.lock` were written in the same second, so their relative
order is not established. Do not read anything into which of those two appears first. The remaining five
are strictly sequential, about 80 seconds apart on the desktop measured.

**Start here on a stuck desktop.** List that directory. The first missing lock
names the phase that failed, and each phase has its own log in `/root/bootstrap/logs/` (see
§3). `[inferred: the lock
set is verified on a live 2026.06 Amazon Linux 2023 desktop, and the naming makes the intent
plain. Whether every OS and every release writes exactly this set is unconfirmed; Windows and the
older releases in particular may differ.]`

Recorded causes, by phase:

| Phase that fails | Cause |
|---|---|
| `pre_install` | Bootstrap bundle could not be downloaded. Egress to the release bucket is blocked, or a proxy is required and not configured |
| `install` | Package installation failed: upstream mirror outage, a build dependency missing for a source-built package, or SSM patching running concurrently |
| `install` | `amazon-efs-utils` fails to build. A 2025 release of that package added a FIPS-related dependency that older RES releases cannot build |
| `install` | Host modules failed to download. Either egress is blocked or the artifact is not present for that version |
| `post_reboot` / config | Active Directory (AD) join failed. Frequently the service account lacks permission to create or modify computer accounts |
| `post_reboot` / config | AD join succeeded but could not resolve a domain controller. Where several controllers exist, one may be unreachable while others work |
| config | DCV configuration failed, usually because DCV packages did not install |
| after `Ready` | User cannot log in: directory sync did not populate a UID/GID, or the home directory on shared storage has a UID/GID from a previous deployment |

**Distinguishing it from a DCV defect (§1.4).** If bootstrap logs are clean through
`linux_vdi_config_host_ready.lock` and the desktop is `Ready`, bootstrap succeeded. A failure after
that point is a session, connection, or identity problem, and isn't a bootstrap problem.

**Distinguishing it from environment misconfiguration (§1.3).** A bootstrap failure caused by RES
shows a RES error in the bootstrap log. A bootstrap failure caused by the environment shows a
network timeout, a DNS failure, a TLS error, or a directory permission denial. Read the log rather
than the state.

**One specific trap.** Custom launch scripts that never run are usually a tagging mistake: the tag
that marks a script for execution belongs on the S3 object, not on the bucket.

### 1.3 Environment misconfiguration presenting as a RES defect

This class ties for first by recurrence and is covered in full in §2.

### 1.4 DCV integration defects

RES uses Amazon DCV for the remote display. DCV is a separate product with its own release cycle,
and a substantial share of user-visible RES failures originate there. RES has no control over
them.

| What you observe | What it usually is |
|---|---|
| Black screen or rendering artifacts after connecting, browser client only, native client fine | A DCV display-server problem, not RES. On non-GPU Linux hosts the recorded remedy is to use the `xdcv` X server rather than stock `Xorg` |
| Connection succeeds then closes immediately, the connection gateway log shows a DNS resolution failure for the desktop | Your DNS cannot resolve the desktop's private name. Test by adding the entry to the connection gateway host's `/etc/hosts`; if that fixes it, the fault is in your DNS |
| The connection gateway log shows a timeout connecting to the desktop, and the desktop's DCV server log shows no incoming traffic | Network path blocked. From the connection gateway host, test reachability of the desktop on TCP 8443 |
| The connection gateway log shows a TLS handshake failure, certificate unknown | Certificate rotation. If certificates are held in Secrets Manager, the secret ARNs recorded in cluster settings must be updated to the new secrets or the connection gateway will fail after rotation |
| The connection gateway connects, but to the wrong address | The DCV server reported an incorrect private name or address. A DCV-side defect; upgrading DCV components is the recorded remedy |
| Windows desktop cannot be connected to after a reboot | A DCV session created before the reboot does not survive it, in some release combinations |
| Windows desktops show 20-25% CPU while idle, against a 2-4% healthy baseline | Not RES. A .NET platform update invalidated the native image cache, and a DCV agent process polling every 15 seconds pays full just-in-time compilation cost on each poll. §1.8 has the update, the mechanism and the workaround |

**How to tell DCV from RES.** Two tests. Does the native DCV client behave differently from the
browser client? If yes, it is DCV, because RES treats both identically. Second, does the RES
session state in the portal agree with the DCV session state on the host? If RES says `Ready` and
DCV has no running session, the failure is between RES and DCV, and the DCV logs on the host are
authoritative.

**What changes at handoff.** These were resolved by escalating to the DCV team. That route does not
transfer. A community maintainer's options are:

- Pin to a DCV version known to work.
- Report through DCV's own public channels.
- Treat the DCV boundary as a hard limit on what RES can fix.

### 1.5 Idle detection and auto-stop defects

The auto-stop path has five stages and each one logs somewhere different. On Linux the control flow is
`[verified]`:

1. A cron entry on the desktop runs once a minute:
   `vdi_idle_check.sh -r <region> -n <environment-name>`.
2. That script reads its thresholds from `/opt/idea/.idle_config.json`, and if that file is absent,
   from the `<environment>.cluster-settings` DynamoDB table (keys under
   `vdc.dcv_session.*`: `cpu_utilization_threshold`, `idle_timeout`, `transition_state`, and the
   helper API URL). It then caches them into that file.
3. It invokes `vdi_auto_stop.py`, which decides idleness and, if idle, calls the VDI helper API
   Gateway endpoint. It will not act within the first 5 minutes of uptime.
4. The helper Lambda performs the stop or hibernate.
5. The VDC controller observes the resulting state change.

Everything up to step 3 logs to `/opt/res/logs/vdi_idle_check.log` on the desktop, including the
decision line, for example `CPU utilization is above threshold. System is not idle.` `[verified]`

| What you observe | What it usually is |
|---|---|
| Desktops stick in `STOPPING` and never reach `Stopped` | The helper Lambda ran out of memory or timed out. **On 2026.06** it is provisioned at 128 MB and 60 s `[verified]`, and raising the memory is the recorded fix. This is also the probable cause of public issue #183. **On 2026.09 the memory is already 512 MB** `[from source]`, with the timeout unchanged at 60 s, so if you see this on 2026.09 the memory is not the answer and the timeout is the next thing to examine |
| Desktops never auto-stop | Check the idle-check log first. If it reports "not idle" each minute, idle detection is working and something on the host is consuming CPU. This is the common case and it is not a defect |
| A desktop stopped, then resumed a few minutes later, and the user says they did not do it | Read the three logs in order: the idle-check log on the host, the helper Lambda log, then the VDC controller log. If the first two are correct, a manual resume is the likely explanation and the VDC controller log will show it |
| A desktop with no schedule ignores the global default schedule | A known defect in some releases, not a configuration error |
| Idle detection is wrong on a multi-core instance | CPU-percentage based idleness averages across cores, so a single busy core on a large instance reads as idle. Known, unfixed |
| Windows idle detection is wrong after a platform update | See the .NET case in §1.8. The load is real; the platform is generating it |

**The important discrimination.** "Auto-stop is broken" is far more often "the desktop isn't
actually idle" than a defect. The idle-check log settles it.

### 1.6 Patch and release mechanics

These failures come from the patch and release process rather than from the product, and they reach
running environments. Verify what a host is running after any patch or rollback.

| What you observe | What it usually is |
|---|---|
| A patch script fails compiling a Python C extension, `Python.h: No such file or directory` | The patch installed a compiler but not the Python development headers. Install the `-devel` / `-dev` package for the host's Python before rerunning |
| A patch produces corrupt JSON or truncated configuration | `base64` was invoked without `-w 0`, so it wrapped lines. This is a difference between Linux and macOS `base64`, and the patch was tested only on macOS |
| A patch fails to download a tool it needs | Your egress is restricted. If a patch cannot fetch its dependencies, bake them into a custom AMI instead |
| After rolling back a patch, a host serves the wrong function entirely | The rollback reverted a launch template to a revision that pointed the host at the wrong module. Verified check below |

**Verifying a host is running the module it should be** `[verified method]`. Each infrastructure
host runs its application under supervisord, with a single program definition in
`/etc/supervisord.d/`. Read it:

- The file name and `[program:...]` name identify the module. On a cluster manager it is
  `cluster-manager`; on a connection gateway host it is `dcv-connection-gateway` with
  `IDEA_MODULE_ID="vdc"`.
- `/opt/idea/app/` contains a directory for the module the host actually installed
  (`cluster-manager`, `virtual-desktop-controller`, `dcv-connection-gateway`).

If the supervisord program name and the `/opt/idea/app/` subdirectory disagree with what the host
is supposed to be, it is running the wrong module and it must be replaced, not repaired. Do this
check after every rollback.

Before applying any patch: read the script, confirm which host operating system it assumes, and
run it on a non-production host of the same OS first. Patch tooling runs from your workstation rather
than on the target platform, so validate a patch on a non-production host before applying it in place.
See the Developer workflow section of
[`../develop/deploying-from-source.md`](../develop/deploying-from-source.md).

### 1.7 Scale and throughput limits

| What you observe | Threshold recorded |
|---|---|
| Throttling on infrastructure hosts or the AWS APIs they call | Approaching roughly 1,000 concurrent desktops |
| `ListSessions` returns a response timeout for users as the population grows | Observed above roughly 1,200 desktops |
| Every portal page shows a request timeout | See §2; at scale it can also be genuine VDC controller saturation |
| Desktops enter `ERROR` in bulk when many are resumed at once | DynamoDB capacity on the session table exceeded |

**The scaling axes are not uniform.** The recorded guidance is to scale
the VDC controller **vertically** and the DCV broker and connection gateway **horizontally**.
Doubling the broker and gateway count resolved bulk `ERROR` states at one large deployment.
Scaling the VDC controller horizontally is not the answer.

`[inferred]` These numbers came from field observation at particular deployments, not from a load
test. A load test to characterize the limits was still an open action item when AWS stopped work.
Treat them as the order of magnitude at which problems began somewhere, not as a supported
envelope.

One further contributor was recorded but never confirmed: a code path forcing renewal of an identity
token on every request rather than using a cache. That would make the timeout worse as the user count
rises.

### 1.8 Windows desktop failures on record

`[unverified]` Each of these was seen in the field with a diagnosed cause, rather than reproduced
here. Check this list before
treating a Windows desktop failure as a new defect. Windows log paths are in §3.3.

**Stuck in `PROVISIONING`.** Four distinct causes are on record:

1. **The DCV Session Manager service starts late.** Its service is configured for delayed start, so RES
   can call create-session before the agent is listening. Mitigation was to delay the create call.
2. **A custom launch script replaced the standard AD join.** Customers who disable the built-in domain
   join and implement their own need an **additional reboot** after their scripts run, which RES does not
   perform for them.
3. **`Get-DDBItem` rejected the payload** because a required `Version` parameter was missing.
4. **Creating a software stack from a Windows session appears to hang.** Windows AMI creation can take up
   to **45 minutes**; the dead-letter queue timeout was extended to 60 minutes to accommodate it. Check
   elapsed time before assuming failure.

**Ready but cannot connect.** An older DCV session manager agent reported the wrong private DNS name or
IP to the DCV broker, so the connection gateway connected to the wrong address and timed out. Published as GitHub
issue **#134** for 2025.09 and earlier. Some customers worked around it by rebooting the desktop, and the
root cause of the reboot dependency was never fully established in at least one case.

**Sustained high CPU when idle, and idle detection stops working.** The cause is entirely outside
RES. .NET Framework cumulative update **KB5065962** (2026-07-15)
invalidated the native image cache, and the NGEN rebuild tasks that would normally repair it run only
when the machine is idle, which it never becomes. `powershell.exe`, spawned by
`dcvsessionmanageragent.exe` on a 15-second probe loop, then pays full JIT cost on every launch, roughly
25 times the normal cost. Desktops sat at 20 to 25 percent CPU against a healthy baseline of 2 to 4
percent, which is enough to defeat RES idle detection and auto-stop. Manual fix confirmed on test
instances: `ngen executeQueuedItems`.

**Startup scripts not downloading.** Reported on an isolated VPC. Logs showed a download-and-execute
error, and it was treated as a networking or S3 bucket configuration problem rather than a RES defect.
See §2.

**Shared storage not mounting.** FSx for NetApp ONTAP failed to auto-mount on Windows desktops, pending
the customer's own `MountSharedStorage.bat`.

**Launch failing outright.** Recorded once as an old DCV package version baked into the default Windows
AMI.

---

## 2. Failures that are not RES

Environment misconfiguration accounted for half the recurring failure themes. It presents as a RES
defect, so the investigation starts in the wrong place and stays there, which is why this section
comes before the log tables and the ladder.

Two habits prevent most of the loss:

- **When a failure appears without a RES change, suspect your environment first.** Ask what
  changed: DNS, certificates, directory, network routes, security groups, proxies, AMIs, patch
  windows, upstream mirrors.
- **Trust the error text over the ticket title.** Reported titles were repeatedly misleading. One
  report titled as a client version mismatch was a Lambda timeout. The observable error in the log
  is the evidence; the title is a guess.

### 2.1 Network

| Symptom | Cause | Test |
|---|---|---|
| **Every** portal page returns a request timeout, and the API health check fails | An isolated VPC with no proxy configured. Amazon Cognito has **no VPC endpoint**, so in a VPC with no internet path the backend Lambda and the infrastructure hosts cannot reach it at all. The proxy parameters must be set | Read `/aws/lambda/<env>-backend-lambda`. TLS handshake timeouts reaching Cognito confirm it. Check whether the proxy and no-proxy parameters were left empty at deployment |
| One API times out, others are fine | Cross-AZ latency. Some calls hop from the cluster manager to the VDC controller. If those hosts are in different Availability Zones, only the calls that hop are slow | Confirm the AZ of both infrastructure hosts. Remedy is to put them in the same AZ: remove the other AZ's subnet from one Auto Scaling group and let it replace the host |
| Portal shows a request timeout intermittently, all APIs | Undersized infrastructure host. Disk, memory or the logging process saturates | Check host metrics and the target group health, before anything else |
| Desktop bootstrap times out downloading packages | Egress blocked, or an upstream distribution mirror outage. Bootstrap has no retry and no mirror fallback | Check whether the same failure occurs from a bare instance in the same subnet |
| Desktop reaches `Ready`, connection closes at once | DNS or routing between the connection gateway and the desktop. §1.4 and §3 | From the connection gateway host, resolve the desktop's private name and test TCP 8443 |
| Connection fails only for some users or some networks | Client-side. Access to the portal and the connection gateway is IP-restricted at deployment; a user on a different network is outside the allowed range | Compare the affected user's source address to the configured ranges |

A completely dead portal in a private VPC is almost always the missing proxy configuration and the
Cognito endpoint gap.

### 2.2 Identity and AD

This is where the boundary is hardest to see, because RES failures and directory
misconfigurations produce the same symptoms.

| Symptom | Cause | How to be sure |
|---|---|---|
| Desktop stalls in `Provisioning`, then `Error`, and the cluster manager log shows insufficient permission to modify a computer account, or an encryption type not permitted | Your service account cannot create or modify computer accounts in the target organizational unit. Not a RES defect | The error names the distinguished name it failed on. Grant the account the documented computer-account permissions |
| `Failed to initialize credentials using keytab: Preauthentication failed` in the directory client log | The host's Kerberos machine credentials are out of sync with the directory | Resynchronize the host's credentials with the directory using a directory administrator account |
| Some desktops fail AD join, others succeed, identically configured | One domain controller is unreachable or misbehaving while others work. Instances that happen to select the bad one fail | Search the **whole** cluster manager log, not a sample. This is only visible in aggregate. An extract covering a few instances will hide it |
| Users or groups missing from RES, or present but missing a UID or GID | Directory sync could not read them, or they lack required attributes such as an email address | Read the `ad-sync` log group. It states which case it hit |
| Users and groups live in different domains of a forest and sync incompletely | **RES does not support AD forests.** Recorded repeatedly as an unresolved limitation. Not a defect to be diagnosed | If you use a forest, this is the answer, and there is no configuration that fixes it |
| Desktop is `Ready`, user cannot log in, `id <user>` says no such user | Directory sync did not populate the user. Read the directory sync log |
| Desktop is `Ready`, user cannot log in, and their home directory has a different UID/GID than the user | Shared storage has a home directory from a previous deployment where the same name had a different numeric ID | Compare `ls -ln /home` against `id <user>`. Removing the stale home directory and launching a new desktop is the recorded remedy |
| User will not enter a password and expects a smart card to suffice | Not supported by RES, and configurable only in the native DCV client rather than the browser | Not a defect |
| Sign-in fails for users whose email contains a `+` | A defect in some releases, not a directory problem. Check known issues |

### 2.3 Configurations that are outside what RES supports

The configurations below were recorded as being closed on this basis.

| Configuration | Position |
|---|---|
| Users created directly rather than through the supported provisioning path | Unsupported. Users must arrive through the intended path |
| AD forests | Not supported |
| Modified RES bootstrap code | Out of scope. Modifying bootstrap and then reporting a bootstrap failure cannot be diagnosed |
| Custom or hardened AMIs | Supported in principle, but a hardened AMI changes the analysis completely, and disclosing it late invalidates work already done. Say so up front |
| Virtual DCV sessions rather than console sessions | Unsupported, and unnecessary: RES is always one user to one desktop |
| Custom domains | Supported, but the certificate lifecycle becomes yours. Rotation without updating the secret references in cluster settings will break the connection gateway |

If you are running any of these and hit a problem, reproduce it on a stock configuration before
concluding that RES is at fault. If it does not reproduce, your modification is the cause.

### 2.4 A cheap triage sequence

Before investigating any failure as a RES defect, run through this, which takes minutes and settles most
cases.

1. **Have you read the known issues for your exact release?** The wiki page index and the issue list
   on GitHub, both linked in §5.1. A share of desktop failures are known defects with a documented
   workaround, and this is the cheapest check there is. §5.1 is how to search those sources without
   being defeated by their keyword matching, and §5.2 onwards is a catalogue of symptoms already seen
   in support.
2. **What changed?** Nothing on the RES side changed in most of these failures. Something in the
   environment did.
3. **Does it reproduce in a second region or a second deployment?** If not, it is local.
4. **Does it reproduce from a bare instance in the same subnet?** If yes, it is the network or the
   AMI. This is rung 1 of the ladder in §4.
5. **Is the error in a RES log or in an AWS API response?** RES stack trace means investigate RES.
   Timeout, DNS failure, TLS failure, throttle, access denial means investigate the environment.
6. **Is any part of the deployment non-stock?** Custom AMI, custom domain, isolated VPC, proxy, your
   own directory, modified bootstrap. Each has a known failure mode above.

Two further habits from the operational record. Reproduce before investigating: an unreproducible
report is not yet a defect. And check the measurement before believing it: one investigation into
a cost spike found the reporter was averaging a metric that should have been summed.

---

## 3. Log locations, consolidated

The paths below were verified on a running RES 2026.06 deployment unless marked otherwise. Paths differ
between releases; check before trusting them on an older one.

### 3.1 Infrastructure hosts (cluster manager, VDC controller, connection gateway)

All three have the same layout `[verified]`.

| Path | What it holds |
|---|---|
| `/opt/idea/app/logs/application.log` | The RES application log. This is the primary log on an infrastructure host |
| `/opt/idea/app/logs/application.log.YYYY-MM-DD` | Rotated daily |
| `/opt/idea/app/logs/stdout.log` | Whatever the process wrote to stdout and stderr before logging was configured. Short, and the place to look when the application will not start at all |
| `/root/bootstrap/logs/userdata.log` | Userdata execution, traced with `set -x`. Shows which module and environment the host was told to be |
| `/root/bootstrap/logs/install.log.<epoch>` | Package and dependency installation. The largest bootstrap log and where most bootstrap failures land |
| `/root/bootstrap/logs/install_app.log.<epoch>` | Installation of the RES application payload |
| `/root/bootstrap/semaphore/*.lock` | Bootstrap phase completion markers. On an infrastructure host: `pre_install_finished`, `install_finished`, `app_installed`, `instance_ready` |
| `/var/log/supervisord.log` | Whether the application process is being started and restarted. `startsecs=30`, `startretries=10`, so a crash loop shows here as repeated starts |
| `/var/log/cloud-init-output.log`, `/var/log/cloud-init.log` | Everything before RES bootstrap took over |
| `/var/log/sssd/` | Directory client. Present and populated on the cluster manager, which joins the domain; effectively empty on the VDC controller and connection gateway hosts |
| `/root/bootstrap/reboot_required.txt` | Whether bootstrap requested a reboot |

Connection gateway hosts additionally have `[verified]`:

| Path | What it holds |
|---|---|
| `/var/log/dcv-connection-gateway/gateway.log` | The DCV connection gateway's own log, owned by `dcvcgw`. Authoritative for connection failures to a `Ready` desktop |

The application runs under supervisord, not systemd. `systemctl status` won't show it. Use
`supervisorctl status`, and read `/etc/supervisord.d/<module>.ini` to see what the host is
configured to run `[verified]`.

### 3.2 Linux virtual desktops

| Path | What it holds |
|---|---|
| `/opt/idea/app/logs/application.log` | Desktop-side RES application and bootstrap-configuration log. Contains the session state transitions (`INITIALIZING`, `READY`) and the DCV configuration steps. The first log to read for a desktop that will not become `Ready` |
| `/root/bootstrap/logs/userdata.log` | Userdata execution |
| `/root/bootstrap/logs/install.log.<epoch>` | Package installation, pre-reboot |
| `/root/bootstrap/logs/install_post_reboot.log.<epoch>` | Post-reboot installation. Only desktops have this phase |
| `/root/bootstrap/logs/install_app.log.<epoch>` | RES desktop application payload |
| `/root/bootstrap/semaphore/*.lock` | Phase markers. See the table in §1.2 |
| `/root/bootstrap/res_installed_all_packages.log` | Summary marker of package installation |
| `/var/log/dcv/server.log` | DCV server. Authoritative for "the session will not start" and "the connection is refused" |
| `/var/log/dcv/agent.console.log` | DCV agent for the console session. Large and chatty |
| `/var/log/dcv/sessionlauncher.log` | Session creation attempts |
| `/var/log/dcv/agentlauncher.<user>.log` | Per-user agent launch |
| `/var/log/sssd/sssd_<domain>.log` | Directory authentication for that domain. Where Kerberos and LDAP failures appear. This is the log for "the desktop is `Ready` but the user cannot log in" |
| `/var/log/sssd/sssd_pam.log`, `sssd_nss.log`, `ldap_child.log` | Authentication, name resolution, and LDAP child process |
| `/opt/res/logs/vdi_idle_check.log` | Idle detection, one entry per minute, including the idle decision |

`[verified]` On 2026.06 Amazon Linux 2023 there is **no** `/var/log/dcv-session-manager-agent/`
directory and no session manager agent service. Installed DCV packages are the server, the
`xdcv` X server, and the web viewer. Older runbooks and older releases refer to a session manager
agent log; do not expect it on a current deployment.

`[verified correction]` Some existing runbooks give the desktop application log directory as
`/opt/idea/app/log/` (singular). The actual directory is `/opt/idea/app/logs/`.

### 3.3 Windows virtual desktops

No Windows desktop was launched during the work behind this document, so the log paths below are
`[inferred]` from documentation rather than `[verified]`. The diagnosed Windows failure patterns are in
§1.8.

| Path | What it holds |
|---|---|
| `C:\Users\Administrator\RES\Bootstrap\Log` | Bootstrap logs |
| `C:\Program Files\RES\app` | RES desktop application logs |
| `C:\ProgramData\NICE\dcv\log\` | DCV server and agent |
| `C:\ProgramData\NICE\DCVSessionManagerAgent\log\` | Session manager agent, where present |
| `C:\Windows\System32\config\systemprofile\AppData\Local\NICE\dcv\` | DCV certificate material |

### 3.4 CloudWatch log groups

The log groups below were verified present on the reference deployment. `<env>` is the environment
name.

| Log group | Source |
|---|---|
| `/<env>/cluster-manager` | Cluster manager `application.log`, stream `application_<ip>` |
| `/<env>/vdc/controller` | VDC controller `application.log` |
| `/<env>/vdc/dcv-connection-gateway` | Connection gateway `application.log` **and** `/var/log/dcv-connection-gateway/*.log`, in separate streams |
| `/<env>/virtual-desktop-app` | All desktops. Streams are keyed by session, not by instance: `<session-id>/bootstrap/logs` and `<session-id>/nice/dcv/log` |
| `/<env>/ad-sync` | Directory sync. The log for "users or groups are missing in RES" |
| `/aws/lambda/<env>-backend-lambda` | The portal's API backend. First stop for portal-wide errors |
| `/aws/lambda/<env>-vdc-vdi-helper-lambda` | Stop, start and hibernate actions on desktops |
| `/aws/lambda/<env>-vdc-custom-credential-broker-lambda` | Credential brokering during desktop bootstrap |
| `/aws/lambda/<env>-scheduled-ad-sync` | Scheduled trigger for directory sync |
| `/aws/lambda/<env>-vdc-scheduled-event-transformer` | Schedule-driven desktop actions |
| `/aws/lambda/<env>-ec2-event-xformer` | EC2 state-change events into RES |
| `/aws/lambda/<env>-cluster-settings-table-event-handler` | Reacts to cluster settings changes |
| `/aws/lambda/<env>-post-auth-cognito-trigger-workflow-lambda`, `<env>-cognito-sync-lambda` | Sign-in and user-pool synchronization |

`[verified]` There is **no** `/<env>/vdc/dcv-broker` log group on 2026.06. The DCV broker was
removed. Documentation and runbooks written before that still reference it; on a current deployment
its absence is correct, not a fault.

`[inferred]` Lambda log groups only exist once the function has been invoked. If one in the table
above is missing, the likeliest explanation is that the function has never run in that
deployment.

### 3.5 Bootstrap logs are not centralized

**Bootstrap installation logs are not shipped to CloudWatch.** Verified: the CloudWatch agent
configuration on every host type collects only `/opt/idea/app/logs/**.log` and, on desktops and
gateways, the DCV logs. `/root/bootstrap/logs/` is not collected anywhere.

**If a desktop fails during bootstrap and is then terminated, the logs that explain the failure are
destroyed with the instance.** They exist only on local disk. Centralizing them was raised as work
and never completed.

Practically, this means:

- When a desktop fails to bootstrap, get onto the instance and copy `/root/bootstrap/logs/` off it
  **before** anything terminates it. Failed desktops do get cleaned up.
- If you need repeat diagnosis of bootstrap failures, add `/root/bootstrap/logs/*` to the
  CloudWatch agent's collect list yourself. There's no reason it can't be collected; it just isn't.

### 3.6 Which log answers which question

| Question | Read |
|---|---|
| Why will the application not start on an infrastructure host? | `stdout.log`, then `/var/log/supervisord.log` |
| Why did a desktop never become `Ready`? | The desktop's `application.log`, and `semaphore/` to locate the phase |
| Why did bootstrap fail? | `/root/bootstrap/logs/install*.log` on the instance, and get it before termination |
| Why can I not connect to a `Ready` desktop? | The connection gateway's `gateway.log`, then the desktop's `/var/log/dcv/server.log` |
| Why can a user not log in to a `Ready` desktop? | Desktop `/var/log/sssd/sssd_<domain>.log`, then the `ad-sync` log group |
| Why is a user or group missing from RES? | `/<env>/ad-sync` |
| Why did a desktop not auto-stop, or stop unexpectedly? | Desktop `/opt/res/logs/vdi_idle_check.log`, then the helper Lambda log, then the VDC controller log, in that order |
| Why does every portal page fail? | `/aws/lambda/<env>-backend-lambda` |
| Why is one API slow when others are fine? | Cluster manager and VDC controller `application.log` for the same window; see §2.1 on cross-AZ latency |

### 3.7 Collecting a diagnostic bundle

There is no tool for this. If you are handing a failure to someone else, or filing an issue, the
set worth collecting is:

1. Both infrastructure hosts' `/opt/idea/app/logs/application.log`, for the failure window.
2. The affected desktop's `/opt/idea/app/logs/`, `/root/bootstrap/logs/`, `/var/log/dcv/`, and
   `/var/log/sssd/`, taken from the instance before it is terminated.
3. The `ad-sync` log group for the same window, if identity is implicated.
4. The connection gateway's `gateway.log`, if connection is implicated.
5. The Auto Scaling group activity history for the infrastructure groups, which shows whether
   hosts have been cycling.
6. The output of `ls /root/bootstrap/semaphore/` on the affected host.
7. Your release version, region, and whether you use a custom AMI, a custom domain, an isolated
   VPC, a proxy, or your own directory.

---

## 4. The VDI failure isolation ladder

When logs and known issues do not resolve a desktop failure, reconstruct the desktop: rebuild it from
the bottom up, one layer at a time, and see which layer introduces the failure. Each rung splits the
search space between RES and not RES.

**Do the cheap work first.** The triage sequence in §2.4, the cause sets in §1.2 and §2, and the
release's known issues resolve most desktop failures for a fraction of the effort. Come here when they
have not. Bring the logs listed in §3, collected while the failure was happening. A log extract from a
different window is worse than none, because it looks like evidence.

Five rungs, in order.

### Rung 1. A bare instance from the same AMI

Launch a standalone EC2 instance from the same AMI the desktop uses. No RES. Install by hand only
what is needed to provoke the symptom; for a display problem that means installing DCV yourself.

- **Reproduces.** The failure is in the AMI, the operating system, or a component RES merely
  installs. It isn't a RES defect, and no amount of RES investigation will help.
- **Does not reproduce.** Continue.

### Rung 2. The same AMI plus the RES desktop userdata

Launch a standalone instance from the same AMI and give it the userdata a RES desktop receives, still
with no RES infrastructure orchestrating it.

- **Reproduces.** The failure is in desktop bootstrap. Go to rung 4.
- **Does not reproduce.** The failure is in RES infrastructure rather than in the desktop: the
  VDC controller, the connection gateway, the cluster manager, or their interaction. Investigate from
  the VDC controller log.

`[inferred]` The reasoning here is that userdata is the boundary between what RES infrastructure
orchestrates and what the desktop does to itself. How faithfully userdata can be reproduced by hand
outside a RES launch is unconfirmed; it includes the environment name and region and may include
per-session values that a hand-built instance cannot obtain.

### Rung 3. The same AMI plus the install scripts directly

Run `install.sh` and `install_post_reboot.sh` from
`source/idea/idea-bootstrap/resources/scripts/virtual-desktop-host/linux/` on a bare instance,
without the surrounding userdata.

- **Reproduces.** A package is failing to install, or installing something that breaks the host.
  Read the install log; installation failures almost always leave one.
- **Does not reproduce.** The failure is in the configuration work that happens after
  installation. Go to rung 4.

### Rung 4. Bisect the configuration step

The configuration phase is Python, not shell:

- Linux: `source/idea/idea-virtual-desktop/src/ideavirtualdesktop/app/linux/bootstrap.py`
- Windows: `source/idea/idea-virtual-desktop/src/ideavirtualdesktop/app/windows/bootstrap.py`

Disable configuration steps individually and rerun until the failure disappears. The step you
removed last is the one at fault. Use `/root/bootstrap/semaphore/` (§1.2) to confirm how far
each attempt actually got, rather than inferring it from the symptom.

### Rung 5. Bisect the install step

If rung 3 reproduced, do the same inside the install scripts: comment out package installations in
sections until the failure clears. Check the install logs carefully first, because in most cases
the failing package does emit an error and bisection is unnecessary.

### Notes on using the ladder

Rungs 1 to 3 each take a full instance launch, so the ladder is slow. Do not skip rung 1 to save
time; investigating a RES defect that turns out to be an AMI problem costs far more than one
instance launch.

`[inferred]` The ordering within rungs 4 and 5 is presented as bisection. In practice, read the logs
first and go straight to the step they implicate; bisection is the fallback when they name nothing.

---

## 5. Symptoms seen in the field

This section is organized by observable symptom and is unverified. §1 covers the same ground organized
by cause class and is verified. Start here if your symptom is concrete.

Entries in this section are marked `[unverified]`: none was re-verified on a running deployment, so
treat each as a strong prior rather than a confirmed fact. Where an entry contradicts §1.1 to §1.7,
which were verified, those sections win. §1.8 is itself `[unverified]`, so it carries no such
precedence.

Use this section after §2.4's triage sequence and alongside §3, and before the isolation ladder in §4:
matching a symptom here is cheaper than reconstructing a desktop.

### 5.1 Search the published known-issue sources before pattern-matching

The public sources change independently of this document, so query them first.

- **The wiki page index** at `https://github.com/aws/res/wiki/_pages`. Page titles carry the affected
  versions, in the form `(2025.06 and 2025.06.01) <symptom>`, which makes filtering to your release
  cheap.
- **The issue list** at `https://github.com/aws/res/issues?q=is%3Aissue`. Issues titled with a version in
  brackets or parentheses are curated known issues; the rest are customer bug reports. Both are worth
  scanning.
- **Keyword search misses more than you'd expect.** Search is conjunctive across terms in a title,
  so a symptom described differently by the reporter will not match. **If a keyword search returns two
  hits or fewer, stop searching and scan the full page index and the unfiltered issue list by eye**,
  filtering on operating system, RES version and affected component.
- **Check whether the fix already shipped** before applying any patch. A workaround for a defect
  corrected in a later release costs more than the upgrade.

Search by three things in turn: the RES version, the exact error string from the log, and the symptom in
the reporter's words.

### 5.2 Desktop lifecycle

`[unverified]`

| Symptom | Cause | What to check | Resolution |
|---|---|---|---|
| Desktops enter `ERROR` after a reboot or resume, roughly one in ten | A DCV session is requested before `dcvserver` is running. Boot-time agents (endpoint security, container runtimes, SSSD) delay DCV startup past the point RES assumes it is up | SSM command history for a failed `dcv create-session`, and the log line `Could not create session. The dcvserver service is not running` | AWS shipped a patch that checks DCV server state before signalling reboot completion. It applies to newly created desktops only, so existing ones need recreating |
| A desktop fails validation permanently, even after DCV is healthy | The validation attempt counter persists in DynamoDB and does not reset on stop or start. The default ceiling is 50 | The log line `Validation ERROR. count: 51`, then the `<env>.vdc.controller.user-sessions-counter` table | Delete the counter item for that session, keyed on `idea_session_id`. Raising the threshold only defers it |
| Windows desktops report `Error retrieving session connection information. Please reboot the Virtual Desktop and try again.` while Linux is fine | RES signals reboot completion and creates the DCV session before Windows has finished rebooting, so the session is lost | Compare timestamps: a session reported ready **before** the DCV server restarted is this defect | Reboot from the portal as a workaround. Fixed by a desktop application package update |
| A desktop sits in `PROVISIONING` and never leaves | Usually several environment faults at once rather than one defect | Run `ldapsearch` from the cluster manager; check the broker target group health and its outbound security group rules; check `IsLoadBalancerInternetFacing`; check free disk on the cluster manager; check custom DNS resolution | Cycle the cluster manager after any AD change, fix the security group, set SSSD `enumerate=false`, correct the prefix list |
| Every desktop fails for one user while others are unaffected | Per-user state rather than a global fault | Stale items for that user in `user-sessions-counter`, and Cognito group membership and precedence | Delete the stale items; set group precedence |

### 5.3 Connection failures

`[unverified]`

| Symptom | Cause | What to check | Resolution |
|---|---|---|---|
| Desktop is `Ready`, the connection hangs on "Starting connection" and times out | A DCV session manager agent old enough to carry a known defect: the connection gateway is given the wrong private DNS name. Seen on AMIs around three months old | Connection gateway logs for the hostname it dialed. A timeout to an unexpected `ip-x-x-x-x.<region>.compute.internal`, or a TLS `close_notify`, is this defect | Rebake the RES-ready AMI with a current DCV agent. **Verify in the connection gateway log before calling this a network problem**: this symptom was repeatedly misdiagnosed as a prefix-list fault |
| The connection gateway looks healthy and connections fail silently | The connection gateway health check is off by default when RES is deployed against customer-owned external resources | Whether the health check is enabled at all | Enable it |
| `Could not create console session: Could not acquire dcv licenses: No license for product (-1)` | DCV licensing configuration | Reachability of the license server and the licensing configuration | Correct the configuration |
| Connections fail for some users and not others on the same network | The client address is not in `<env>-prefix-list` | The prefix list against the user's egress address | Add the correct ranges. Widening to `0.0.0.0/0` is a diagnostic step, not a fix, and should be reverted |
| An NLB listener disappears after toggling QUIC and is not recreated | Toggling QUIC with an empty `custom_tags` value | Whether `custom_tags` is empty | Set a non-empty value before toggling |

### 5.4 Proxy handling differs between Windows and Linux

`[unverified]` On Windows, RES overwrites the SSM agent's `NO_PROXY` with `169.254.169.254`
alone, which breaks the DCV session manager agent's path to the broker. The visible symptom is a desktop
taking around thirty minutes to become ready, with repeated connection errors in the agent log. The Linux
SSM agent respects the system-wide `no_proxy`, so the fault is Windows-only. The workaround in use is a
script that rewrites the agent's proxy configuration after the desktop starts.

### 5.5 Portal and API

`[unverified]`

| Symptom | Cause | What to check | Resolution |
|---|---|---|---|
| With several hundred desktops, some do not appear in the portal, including a user's own | Two defects: a missing user lookup, so the filter does not apply; and a DynamoDB scan-and-filter that stops paginating at the first empty page | Browser developer tools: `ListSessions` returning empty with a cursor present is the pagination defect | Both were fixed by patches; check whether your release contains them |
| Non-administrators cannot share a desktop | The permission-profile listing call blocks non-administrators | Whether the caller is an administrator | Check for a release containing the fix |
| The software stacks page is blank or short | Rendering, seen with an SSM parameter ARN supplying allowed instance types | Whether allowed instance types come from an ARN rather than literal values | Use literal values |
| The portal times out | Load, undersized infrastructure hosts, or DynamoDB throttling | Instance sizes, DynamoDB capacity, ALB target response times | Scale the constrained layer |

### 5.6 Identity and directory

`[unverified]`

| Symptom | Cause | Resolution |
|---|---|---|
| Directory sync completes but finds no users in a group | LDAP filter, nested groups, or LDAPS reachability | Verify the filter and test `ldapsearch` from the cluster manager |
| A Linux desktop fails to join the domain during bootstrap | OS-specific realm and SSSD behavior, recorded on RHEL 8.10 | Read the bootstrap log for the specific failure |
| An automated security finding says Cognito self-registration is enabled | RES enables it by default | Disable it if you do not need it |
| A user in several Cognito groups cannot log in | No precedence set between the groups | Set group precedence |
| An SSO user cannot reach a desktop although sync succeeded | User mapping or group assignment | Confirm the user synced and holds the expected group |

### 5.7 Upgrade and installation

`[unverified]` For the 2026.09 upgrade specifically, see
[`../operate/upgrading-to-2026.09.md`](../operate/upgrading-to-2026.09.md).

- **A CloudFormation change set fails during a version upgrade.** Incompatible parameter changes or
  nested-stack conflicts. **RES does not support updating template parameters on an existing stack**, so
  do not treat that as an upgrade path.
- **Snapshot apply fails at a major version upgrade.** Version-specific migration behavior; read the
  release notes for prerequisites before starting.
- **Installation fails when pointed at an existing Cognito user pool.** Recorded against 2025.12. A new
  pool is the reliable route.
- **The CDK bootstrap stack fails with IAM denials, and the main stack then fails on a wait condition.**
  Diagnosed on 2025.06 and 2025.06.01. The installer's role carries an inline policy whose ECR and SSM
  statements are conditional on the environment-name resource tag. During *creation* the repository and
  the SSM parameter do not carry that tag yet, so the condition is false and the action is denied.
  The visible errors are `not authorized to perform: ecr:SetRepositoryPolicy on resource ... cdk-*-container-assets-*`
  and `not authorized to perform: ssm:ListTagsForResource on ... /cdk-bootstrap/*/version`, followed by
  `WaitCondition received failed message` on the main stack. Three things about recovering from it are
  worth knowing whatever release you are on, because they are properties of the installer rather than of
  that defect:
  - **A wait condition cannot be re-signalled.** Once it has received a failure the main stack is
    finished, whatever you repair underneath it.
  - **The bootstrap stack and the installer role are children of the main stack**, so deleting the main
    stack removes them, and any hand-applied IAM fix goes with them.
  - **Deploy with `--disable-rollback` when you expect trouble**, so the failed resources survive for
    inspection instead of being cleaned up before you can read them.

  A redeploy usually succeeds where the first attempt failed, because the role's policy has had time to
  propagate before the installer task runs. That is a timing dependency rather than a fix.

### 5.8 AMI and image build

`[unverified]` These refine the `install` row in §1.2 rather than replace it: that row records
an `amazon-efs-utils` build failure with a FIPS-related cause, and there are two further causes for
the same visible failure.

| Symptom | Cause | Resolution |
|---|---|---|
| Ubuntu 22.04 desktops fail to provision, `supervisord` will not start with `ModuleNotFoundError: No module named 'pkg_resources'` | `python3-setuptools` 82.0.1 removed the deprecated `pkg_resources`, which the pinned Supervisor release needs | Pin install scripts to a specific release URL rather than `latest`. A later RES release moves Supervisor to a version that does not need it |
| Ubuntu 22.04 and 24.04 desktops fail to launch, bootstrap reports `lock file version 4 requires -Znext-lockfile-bump`, EFS is not mounted and login fails because `/home` is missing | `efs-utils` upstream moved its `Cargo.lock` to version 4, which needs a newer Rust toolchain than the image provides | Published as a wiki page and as issue 163 in the public repository, with a patch; fixed in a later release |
| RHEL 8 and 9 desktops fail the same way, with `rustc 1.79.0 is not supported ... backtrace@0.3.75 requires rustc 1.82.0` | The same package pulls a dependency needing a newer Rust than RHEL 8 or 9 ships | Install a current Rust toolchain before building `efs-utils`. Issue 129 in the public repository; fixed in a later release |

Both `efs-utils` entries are the class of failure
[`../reference/external-dependencies.md`](../reference/external-dependencies.md) warns about: a
third-party dependency changed and RES had no pin protecting it.

### 5.9 Infrastructure and performance

`[unverified]`

- **Configuration changes do not take effect on running infrastructure hosts.** Secrets, CA certificates
  and template parameters are read at boot. Terminate the host and let the scaling group replace it,
  which takes fifteen to twenty minutes.
- **Consolidating infrastructure hosts degrades performance.** Moving from several nodes to one requires
  a larger instance, not the same instance carrying more load. Watch target group response times.
- **Auto-stop does not fire.** Check the VDC controller logs for scheduling errors and the auto-stop
  configuration.
- **SSSD `enumerate=true` fills the cluster manager's disk**, and the visible failure is application
  crashes rather than anything mentioning disk.

### 5.10 Windows desktops

`[unverified]` §1.8 holds the diagnosed Windows failure patterns. Two additions from the ticket record.
Custom PowerShell scripts do not always receive their arguments through RES bootstrap. Linux custom
launch scripts can fail to execute when their S3 object tags do not match the expected form. Check the
bootstrap log for an attempted execution before assuming the script itself is wrong.

### 5.11 Before you offer a fix

`[unverified]` Before you offer a fix, check:

- **Ask what patches are already applied, before producing a new one.** Cumulative patches conflict, and
  a conflict presents as the fix silently not working.
- Does the patch apply to the customer's exact version?
- Have stale DynamoDB counter items been removed for resources that already failed? A correct fix still
  looks broken while they remain.
- How old is the AMI? Anything over about three months may carry a known DCV agent defect.
- Has the cluster manager been cycled since the last AD, secret or certificate change?
- For a Windows symptom: does it reproduce on Linux? If not, treat the timing and proxy differences in
  §5.4 and §5.10 as the first candidates.
- For a connection symptom: prefix list checked, and `IsLoadBalancerInternetFacing` set as intended?
- Is the configuration one RES supports at all? Managing RES-created instances from outside RES, custom
  AMIs well behind the release, and multi-node arrangements that were later consolidated have all been
  causes.

### 5.12 Failure patterns in how these were diagnosed

`[unverified]` Recurring process faults:

- **Assuming a single root cause.** The longest-running cases had two or three faults at once. Enumerate
  them separately.
- **Providing an untested script or patch.** One case lost days to an indentation error and a patch
  instruction that named the wrong module.
- **Closing before verifying both new and existing resources.** Several fixes applied only to newly
  created desktops, which is not the same as resolved.
- **Concluding "network problem" without connection gateway log evidence.** See §5.3.
- **Changing a stored configuration value without cycling the host that reads it.** See §5.9.
- **Async round trips on an escalated case.** The record is consistent that a live debugging session
  resolves these faster than days of correspondence.

### 5.13 DynamoDB tables worth knowing during diagnosis

`[unverified]` Table names are prefixed with the environment name.

| Table | Holds | Why you would read it |
|---|---|---|
| `<env>.vdc.controller.user-sessions-counter` | Per-session validation attempt counts | Stale items block retries permanently. See §5.2 |
| `<env>.vdc.dcv-broker.dcvServer` | DCV server state as the broker sees it | Disagreement with the instance's real state |
| `<env>.ad-sync.distributed-lock` | The directory sync lock | A lock left behind by a cycled cluster manager stops directory sync silently |
| `<env>.cluster-settings` | Cluster configuration, including `vdi-app.app_package_uri` | Confirms which desktop application package a deployment actually uses, which is how a patched package is applied |

**Reading these is diagnosis. Writing them is not a fix on its own**, because running hosts cache
configuration at boot: see §5.9.
