# External dependencies

> **Note.** This document was written with AI assistance and is not part of the AWS documentation for RES. Treat it as directional: verify anything you depend on against the source tree and your own deployment.

Every artifact outside this repository that a RES deployment touches: who owns it, whether it is
needed once at install time or fetched again on every instance launch, what breaks when it stops
being available, and how to replace it.

RES is supported by AWS until its End of Support Life, after which monitoring these dependencies
becomes the operator's responsibility. Several of them are fetched at *every* instance
launch, from third parties who have no relationship with RES and no reason to preserve compatibility.
One of them has already broken a supported OS in exactly that way, described in §8.

Claims below marked `[verified]` were confirmed by measurement on 2026-09-05, either against a
running RES 2026.06 environment built entirely from public source, or by direct request to the
endpoint concerned. `[verified on 2026.09]` marks the same kind of measurement, made instead against a
2026.09 deployment. `[from source]` means read from the repository. `[inferred]` means neither.

---

## Summary

**Fetch timing** distinguishes *install* (once, when the CloudFormation stack runs), *launch* (again
on every EC2 instance that RES boots, meaning infrastructure hosts and every VDI), and *build* (only when
building or releasing RES).

| Artifact | Owner | When fetched | What breaks if unavailable | Replaceable |
|---|---|---|---|---|
| [`research-engineering-studio-<region>` S3 buckets](#1-the-research-engineering-studio-region-s3-buckets) | AWS | Install, and Launch as a fallback | New installs from published templates; host-module fetch on any deployment not using tiers 1 and 2 | Yes, see §1 |
| [`public.ecr.aws/l6g7n3r5/research-engineering-studio`](#2-the-three-publicecraws-registries) | AWS | Install | AD sync image copy during install; existing environments unaffected | Yes, build locally |
| [`public.ecr.aws/i4h1n0f0/idea-administrator`](#2-the-three-publicecraws-registries) | AWS | Install, as a default | Nothing in the supported path, see §2 | Yes |
| [`public.ecr.aws/g8j8s8q8`](#2-the-three-publicecraws-registries) | AWS | Never, in the supported path | The legacy Windows installer script only | No replacement needed |
| [Host modules (`libnss_cognito`, `pam_cognito`, `ssh_keygen`)](#3-host-modules-the-three-tier-resolution) | AWS (tier 3) or you (tiers 1 and 2) | Launch, every host | User authentication on every new host | Yes, build and publish yourself, §3 |
| [Stock vendor AMIs](#4-stock-vendor-amis) | Amazon, Red Hat, Canonical, Marketplace | Launch | VDI launches, as the pinned IDs age out | Yes, but no regeneration script, §4 |
| [`aws-samples/aws-hpc-recipes` assets](#5-aws-hpc-recipes-assets) | AWS Samples (separate repo) | Install, prerequisites only | Evaluation prerequisite stack | Already vendored, §5 |
| [DCV packages, `d1uj6qtbmh3dt5.cloudfront.net`](#6-dcv-from-d1uj6qtbmh3dt5cloudfrontnet) | AWS (DCV) | Launch, every VDI | Every VDI launch | Mirror only, §6 |
| [EPEL, `dl.fedoraproject.org`](#7-the-rest-of-the-vdi-bootstrap-fetches) | Fedora Project | Launch, RHEL/Rocky VDI | RHEL and Rocky VDI bootstrap | Yes, mirror |
| [FSx for Lustre client repo](#7-the-rest-of-the-vdi-bootstrap-fetches) | AWS | Launch, when Lustre is mounted | Lustre mounts on new hosts | Yes, mirror |
| [`repo.radeon.com`](#7-the-rest-of-the-vdi-bootstrap-fetches) | AMD | Launch, AMD GPU VDI only | AMD GPU desktops | Yes, mirror |
| [`github.com` (pyenv, efs-utils, yq)](#7-the-rest-of-the-vdi-bootstrap-fetches) | Third parties | Launch, every Linux VDI | Python, EFS mounting, YAML parsing during bootstrap. **Has broken already**, §8 | Yes, vendor |
| [`us.download.nvidia.com`, `rpmfind.net`, `sh.rustup.rs`](#7-the-rest-of-the-vdi-bootstrap-fetches) | NVIDIA, community, Rust | Launch, conditional | NVIDIA GPU desktops; one RHEL package workaround; EFS build from source | Yes, mirror |
| [`awscli.amazonaws.com`, SSM agent, CloudWatch agent, mountpoint-s3](#7-the-rest-of-the-vdi-bootstrap-fetches) | AWS | Launch, every host | Bootstrap, observability, S3 mounts | Yes, mirror |
| [`bootstrap.pypa.io/pip/3.7/get-pip.py`](#9-restricted-networks-what-to-allowlist-or-mirror) | PyPA | Install, samples certificate path only | The demo certificate template | Yes, §9 |
| [`acme.sh` tarball on `github.com`](#9-restricted-networks-what-to-allowlist-or-mirror) | acme.sh project | Install, samples certificate path only | The demo certificate template | Yes, §9 |
| [`s3://solutions-build-assets/changelog-spec.yml`](#10-build-time-only) | AWS | Build | The CodeBuild `post_build` phase | No, and not needed, §10 |
| [`viperlight-scanner` on S3](#10-build-time-only) | AWS | Build | The `viperlight_scan` tox environment | Drop it, §10 |

**A self-synthesized install uses none of the AWS-owned artifacts.** A RES install synthesized from
this repository with the `publish_templates` CDK context key unset does not use the AWS-owned buckets
or registries at all.
`[verified]` A `cdk synth` under those conditions produced 11 templates containing zero occurrences
of `research-engineering-studio`, zero of `public.ecr.aws`, zero of `solutions-build-assets`, and
zero of `aws-hpc-recipes`. That deployment then ran to completion under an IAM permission boundary that
denied every role in it access to all four, and a Linux desktop launched and authenticated
successfully. Everything in §1 to §3 below is therefore a migration concern for existing deployments,
not a barrier to a new one.

---

## 1. The `research-engineering-studio-<region>` S3 buckets

### What the buckets hold

One bucket per region, named `research-engineering-studio-` plus the region. They hold two things:

- `releases/<version>/`: the install CloudFormation template, the CDK file assets it references
  (bootstrap scripts, Lambda code, `res-installation-scripts-*.tar.gz`), and the component tarballs.
  Also `releases/latest/`, refreshed from the newest release at the end of the publish pipeline.
- `host_modules/<module>/latest/<arch>/<module>.so`: the compiled PAM and NSS shared objects, which
  is the tier-3 fallback described in §3.

`[from source]` The bucket prefix is `ARTIFACTS_BUCKET_PREFIX_NAME` in `source/idea/constants.py`.
The publish pipeline iterates 18 commercial regions plus 2 GovCloud regions.

### Access, measured

These buckets are world-readable but not listable:

```
$ curl -s -o /dev/null -w '%{http_code}\n' \
    'https://research-engineering-studio-us-west-2.s3.us-west-2.amazonaws.com/?list-type=2'
403

$ curl -s -o /dev/null -w '%{http_code}\n' \
    'https://research-engineering-studio-us-west-2.s3.us-west-2.amazonaws.com/releases/2026.06/ResearchAndEngineeringStudio.template.json'
200
```

`[verified]` Both with no credentials at all. So you can retrieve any object whose key you already
know, and you cannot discover keys you do not know. Keep a record of the keys you depend on; you can't
enumerate them later.

### What is retained

`[verified]` Every release version from 2023.11 through 2026.06 returned HTTP 200 for its install
template, plus `latest`. One gap: `releases/2025.01/` returned 403, consistent with there never having
been a 2025.01 release rather than with deletion. `latest` was byte-identical in size to 2026.06.

Mirror what you depend on into your own account now. Do not build a procedure that fetches from a bucket
you do not own at a time you do not control.

### What breaks when they go

- *Existing deployments that use tiers 1 or 2 for host modules:* nothing. `[verified]`
- *Existing deployments that fall through to tier 3:* every new host fails to install its
  authentication modules. Because that fetch happens at **every** host boot, an environment that
  scales a VDI after the bucket goes away gets a host on which users cannot resolve or log in.
- *New installs from a published template:* impossible. The template and its file assets are both
  in the bucket.

### How to be independent

Do this once, before you need to:

1. `cdk bootstrap` your account and region, so CDK file assets resolve to your own bucket.
2. `invoke build package` to produce the component tarballs and installation scripts.
3. Build and publish the three host modules to `res-staging-<region>-<account-id>` in your own
   account (§3).
4. Build and push the AD sync image to your own ECR repository (§2).
5. `cdk synth ResearchAndEngineeringStudio` with `publish_templates` **unset**, passing
   `-c ad_sync_registry_name=<account-id>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>`.
6. Deploy the template `cdk synth` wrote to `cdk.out/`, not one fetched from a bucket.

`[from source]` The switch is in `source/idea/app.py`: with `publish_templates` set, the stack
synthesizer points file assets at `research-engineering-studio-${AWS::Region}`; without it, at
`res-staging-<region>-<account>`. There is no third mode, and the second one is the default.

### The staging bucket is per account and region, and you cannot change it

`[verified on 2026.09]` The name is built from the account and region alone, with no parameter or context
override. Two consequences:

- Component tarballs are safe, because they are written under `releases/<version>/`.
- **Host modules are not.** They live at `host_modules/<module>/latest/<arch>/`, with no version
  segment, so publishing modules for a second environment **overwrites what the first environment
  fetches at host boot**. Existing hosts keep the copy already installed on local disk, so nothing
  appears wrong until a new desktop launches with modules built for a different release.

A development and production pair in one account is the normal case. If you run more than one
environment in an account, either use a separate account or region per environment, or back up
`host_modules/` before publishing. The last publisher wins.

### Proving independence with a permission boundary

To prove you have succeeded rather than assuming it, use an IAM permission boundary. RES accepts one
as the `IAMPermissionBoundary` parameter and attaches it to every role it creates. Give it an explicit
deny on `research-engineering-studio-*`. An install that completes under that boundary is independent of
the service team's buckets.

One limitation to understand about that test: **an IAM deny cannot stop an unauthenticated fetch.**
Anonymous `GetObject` against these buckets returns 200, as measured above, and IAM only governs
authenticated calls. The test is still sound for host modules, because those are fetched by
`aws s3 cp` running under an EC2 instance role, so the calls are authenticated and the deny applies.
For container images the control is different: the synthesized templates contain no
`public.ecr.aws` reference, so there is nothing to pull anonymously.

---

## 2. The three `public.ecr.aws` registries

Three registry aliases appear in the repository, belonging to three different AWS accounts.

| Alias | Repository | What is actually in it | Referenced from |
|---|---|---|---|
| `l6g7n3r5` | `research-engineering-studio` | 70 tags: `ad-sync-<version>-<commit>`, `installer-<version>-<commit>`, and bare `<version>-<commit>` tags | The publish pipeline |
| `i4h1n0f0` | `idea-administrator` | 5 tags, all IDEA-era: `v3.0.0-pre-alpha-feature`, `v1.0.0-pre-alpha-feature`, and three more. **No AD sync image.** | The install stack's default, and the Linux installer script |
| `g8j8s8q8` | `idea-administrator` | Repository does not exist | The Windows installer script only |

`[verified]` All three were queried anonymously through the ECR public token endpoint and the Docker
Registry v2 tag-list API. No credentials. The `l6g7n3r5` tag list included `ad-sync-2026.06-cd98aa84`
and `ad-sync-2026.09b1-d1d059cc`; the `i4h1n0f0` tag list contained only the five IDEA-era tags; and
`g8j8s8q8/idea-administrator` returned `NAME_UNKNOWN`.

### The default points at the wrong registry

`[from source]` `install_stack.py` defines `PUBLIC_REGISTRY_NAME` as
`public.ecr.aws/i4h1n0f0/idea-administrator:v3.0.0-pre-alpha-feature` and uses it whenever
`ad_sync_registry_name` is not supplied. As the table shows, that registry holds no AD sync
application. It holds an old IDEA administrator image. The tag does exist, so a pull would succeed;
it would simply pull the wrong thing.

`[verified]` The *published* 2026.06 template does not have this problem. Its only `public.ecr.aws`
reference is `public.ecr.aws/l6g7n3r5/research-engineering-studio:ad-sync-2026.06-cd98aa84`, because
the publish pipeline passes `-c ad_sync_registry_name` explicitly.

**If you synthesize the install template yourself, always pass `-c ad_sync_registry_name`.** Falling
through to the default pulls a wrong image rather than failing.

### What breaks

Install-time only. `[from source]` Running hosts never pull the image. A custom resource in the
install stack starts a CodeBuild project that copies the public image into an ECR repository RES
creates inside the environment, and the AD sync task runs from that copy thereafter. `[verified]` The
reference environment has its own ECR repository holding the copy. So losing the public registry
breaks new installs that reference it and leaves existing environments running.

### How to replace it

`[verified]` The image builds from public inputs only, and the build was executed for the first time
during the reference run. Its four inputs are the Amazon Linux 2023 base image from
`public.ecr.aws/amazonlinux/amazonlinux:2023`, yum repositories, a python.org tarball with a pinned
SHA-384, and the `all-<version>.tar.gz` produced by `invoke build package`.

```
invoke build package
invoke docker.prepare-artifacts          # copies all-<version>.tar.gz into deployment/ecr/ad-sync/
docker build -t <repo>:<tag> deployment/ecr/ad-sync
aws ecr get-login-password | docker login --username AWS --password-stdin \
    <account-id>.dkr.ecr.<region>.amazonaws.com
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>
```

Then pass that URI as `-c ad_sync_registry_name=...` at synth time. `[verified]` The image built this
way performed the Active Directory synchronization on the reference environment, with 5 users and 3
groups imported with their AD GIDs, so it is confirmed functionally and not merely as a successful
build.

Note that `tasks/docker.py` has a `publish` task that only tags and never pushes, and a
`print_commands` task whose body is `pass`. `[from source]` Use the commands above rather than those
tasks.

`g8j8s8q8` needs no replacement. It is referenced only by the legacy Windows installer script, which
also pins a 2023 revision, and the repository does not exist.

---

## 3. Host modules: the three-tier resolution

`libnss_cognito`, `pam_cognito` and `ssh_keygen` are Go shared objects that run **as root in the
authentication path** on every RES host. `libnss_cognito` is what makes `getent passwd <user>` return
a directory user; `pam_cognito` authenticates; `ssh_keygen` provisions keys.

They are not baked into an AMI. They are downloaded and installed at every host boot, by
`source/idea/idea-bootstrap/resources/scripts/common/linux/host_modules.sh`, called from the
cluster-manager, bastion-host and Linux VDI install scripts.

### The three tiers

`[from source]` For each module, in order, first hit wins:

| Tier | Source | Condition |
|---|---|---|
| 1 | The S3 URI stored in the DynamoDB cluster setting `cluster-manager.host_modules.<module>.<arch>.s3_url` | `ENVIRONMENT_NAME` is set and the item exists |
| 2 | `s3://<STAGING_BUCKET>/host_modules/<module>/latest/<arch>/<module>.so` | tier 1 empty and `STAGING_BUCKET` is set |
| 3 | `s3://research-engineering-studio-<region>/host_modules/<module>/latest/<arch>/<module>.so` | both above empty |

The bootstrap script fetches the module with `aws s3 cp` under the instance role, then applies
`chmod 555` and `chown root:root`.

**The install stack populates tier 1 from your own staging bucket.** `[verified]` On the
reference environment, all six tier-1 cluster settings, three modules across two architectures,
contained `s3://res-staging-<region>-<account-id>/host_modules/...`. Nothing pointed at an AWS-owned
bucket.

So the AWS bucket is a last-resort fallback rather than the normal path, and an environment installed
correctly never touches it. The verification chain:

`[verified]` MD5 of `libnss_cognito` and `pam_cognito` was identical at three independent points:
compiled on the build host from source, stored as an object in the deployer's own staging bucket, and
loaded on a running desktop. The installed `libnss_cognito` also differed in size from the
AWS-published binary by 673,936 bytes, so the host was demonstrably not running the AWS artifact.
`grep` for `research-engineering-studio` across the entire bootstrap log tree returned zero hits.
Finally `getent passwd` on the desktop resolved a directory user with a UID and GID in the LDAP
ID-mapping range, which only succeeds if the NSS module was fetched, installed, loaded and is
querying the directory.

### What breaks

Runtime, on every host boot, for any deployment that reaches tier 3. It can break a working
environment months after installation, without warning, the first time that environment scales.

### How to build and publish them

`[verified]` All three build from source with Go dependencies resolved entirely from public sources.

Prerequisites on a RHEL-family build host: `gcc`, `glibc-devel`, `pam-devel`, `nss-devel`, `jq`, Go,
and `CGO_ENABLED=1`. `[from source]` Taken from
`source/infra/host_modules_pipeline/docker/Dockerfile.build`. `GOPATH` must be set, because the build is
CGO. It doesn't work from a bare environment.

The build itself, from `source/infra/host_modules/`:

```
for module in $(jq -r '.modules[].name' ./modules.json); do
  go build -buildmode=c-shared -o ./out/${module}.so ./${module}
done
```

`modules.json` lists `test_module`, `ssh_keygen`, `libnss_cognito` and `pam_cognito`. On 2026.09 all are
at 0.2.0 except `ssh_keygen`, which is 0.2.1. `test_module` is not deployed.

Publish with `source/infra/host_modules_pipeline/scripts/publish.sh` and `publish_latest.sh`, setting
`S3_BUCKET_NAME` to publish only to a bucket you own in the current region. Left unset, those scripts
target the staging bucket *and* every regional AWS bucket, which you cannot write to. The layout the
bootstrap script expects is:

```
s3://<your-bucket>/host_modules/<module>/latest/<arch>/<module>.so
```

with `<arch>` being `x86_64` or `arm64`. `publish.sh` refuses to overwrite an existing version, by
design.

Build for both architectures if you run any arm64 desktops. The arm64 tier-1 settings are populated
independently of x86-64, so a missing arm64 module falls through to tier 3 while x86-64 works. That
presents as a failure specific to one architecture.

---

## 4. Stock vendor AMIs

**No RES-built AMI exists.** `[verified]` The desktop launched on the reference environment ran
`ami-...` owned by `137112412989`, alias `amazon`, named
`al2023-ami-2023.11.<date>-kernel-6.1-x86_64`, an unmodified Amazon Linux 2023 image. RES bootstraps
DCV, the host modules and everything else onto a stock image at first boot.

There is no image-build pipeline to inherit. The region-and-OS-to-AMI-ID mapping tables must be
maintained by hand instead.

Two tables:

| File | Purpose |
|---|---|
| `source/idea/infrastructure/resources/config/region_ami_config.yml` | Infrastructure hosts. 24 regions, Amazon Linux 2023 only. |
| `source/idea/infrastructure/resources/config/base-software-stack-config.yaml` | The base VDI software stacks. Per OS, per architecture, per region. |

`[verified]` Owners of the us-west-2 entries, all public images:

| OS | Owner account | Alias |
|---|---|---|
| Amazon Linux 2023 (x86-64 and arm64) | `137112412989` | `amazon` |
| Red Hat Enterprise Linux 9 | `309956199498` | `amazon` |
| Ubuntu 22.04 and 24.04 | `099720109477` | `amazon` |
| Windows Server 2022 | `801119661308` | `amazon` |
| Rocky Linux 9 | `679593333241` | `aws-marketplace` |

Note the last two. The Windows owner is the Amazon Windows AMI account, not one of the three Linux
vendors, and Rocky Linux comes through AWS Marketplace rather than a vendor account, so a
regeneration script has four owner conventions to handle, not one.

### The pins age, and 2026.09 is the last AWS refresh

Two separate measurements exist, against two releases. Read each against its own release and date.
They are not two answers to one question.

**The 2026.06 pins, measured 2026-09-05.** `[verified]` Three of the seven us-west-2 entries were
already past their vendor deprecation date, three months after that release shipped. The dates on the
seven:

| Entry | Deprecates |
|---|---|
| Rocky Linux 9 | 2026-07-08 |
| Amazon Linux 2023, x86-64 | 2026-08-13 |
| Windows Server 2022 | 2026-08-19 |
| Amazon Linux 2023, arm64 | 2026-09-09 |
| RHEL 9 | 2028-05-13 |
| Ubuntu 24.04 | 2028-05-15 |
| Ubuntu 22.04 | 2028-05-21 |

**The 2026.09 pins, measured 2026-09-07.** `[verified]` Both tables were refreshed for that release, and
no us-west-2 pin was past its vendor deprecation date. The earliest of those dates is 2026-11-01. "Not
deprecated" is not the same as "newest": five of the seven us-west-2 identifiers already had newer
upstream images available.

**2026.09 is the final release, so these are the last refreshed pins.** A deprecated public AMI remains
launchable but stops appearing in searches, and is eventually
deregistered. When that happens, VDI launches for that OS fail in that region with an image-not-found
error, and the fix is a table edit rather than anything diagnosable from logs. Take ownership of the
mapping, and check the dates yourself on the schedule below.

### Rocky Linux is in the table but is not a base stack

`[verified]` A Rocky Linux 9 entry exists in the software stack config but no Rocky stack was created
on the reference environment: only six stacks appeared, covering AL2023 x86-64 and arm64, RHEL 9,
Ubuntu 22.04, Ubuntu 24.04 and Windows. `[inferred]` Rocky is presumably available for custom stacks
rather than base ones.

### There is no regeneration script

Nothing in this repository regenerates either table. The lookup for each vendor is an SSM public
parameter or a `describe-images` filter against the owner account, for example:

```
aws ssm get-parameter --region <region> \
  --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64 \
  --query Parameter.Value --output text
```

for Amazon Linux, and `describe-images --owners <owner> --filters Name=name,Values=<pattern>` sorted
by `CreationDate` for the rest. Until such a script exists, an operator can update a single region
and OS by hand, since each file is a per-region list.

Check `DeprecationTime` on every entry you rely on, in every region you deploy to, at least twice a
year:

```
aws ec2 describe-images --region <region> --image-ids <ami-id> \
  --query 'Images[0].DeprecationTime' --output text
```

---

## 5. `aws-hpc-recipes` assets

**Already resolved.**

`[verified]` `grep` for `aws-hpc-recipes` and `hpc-recipes` across the RES source tree returns zero
hits; the only remaining mention anywhere in the repository is the provenance record in
`samples/PROVENANCE.md`, which is a citation rather than a fetch.

The dependency was never in the RES code. It was in the deployment *procedure*, which directed a
deployer at CloudFormation templates hosted on behalf of the separately owned
`aws-samples/aws-hpc-recipes` repository. It was also in the `BIStackTemplateURL` CDK context value,
which has no documented source.

That closure now lives in `samples/` in this repository, with per-file checksums and the upstream
commit recorded in `samples/PROVENANCE.md`. `[verified]` Eight of the twelve vendored files are
byte-identical to upstream; four were rewritten, two to redirect cross-repository references inward and
two to fix defects found in a pre-publication review.

`[verified]` The vendored copy was deployed for real, not merely inspected: two nested stacks whose
`TemplateURL` values had been rewritten to a bucket in the deploying account both reached
`CREATE_COMPLETE`, which means CloudFormation fetched and executed the vendored children. The child
templates needed no permission changes, because they build their IAM policies from the S3 path
*parameter* rather than from a hardcoded bucket name. The closure was written to be relocatable.

Read `samples/README.md` before using any of it, because it is demo-grade by design.

---

## 6. DCV, from `d1uj6qtbmh3dt5.cloudfront.net`

Amazon DCV is the remote display protocol the virtual desktops run on. Without it a VDI is an EC2
instance nobody can reach.

`[from source]` `package_config.yml` names this host 64 times, covering three components across every
supported OS and both architectures:

- the DCV server, for each of `amzn2`, `amzn2023`, `el8`, `el9`, `ubuntu2204`, `ubuntu2404`, x86-64
  and aarch64
- the DCV session manager agent, same matrix
- the DCV connection gateway, for the gateway host
- `NICE-GPG-KEY`, the package signing key

`[verified]` The GPG key URL returned 200.

**Fetched at every launch, and unpinned.** Two things about these URLs. First, they
are downloaded during host bootstrap, so every VDI launch and every gateway replacement depends on
this endpoint being up. Second, the URLs contain **no version**. For example
`nice-dcv-amzn2023-x86_64.tgz`, so a host launched today installs whatever DCV version is currently
published there. `[from source]` The `sha256sum` for each package is fetched from the *same* host
alongside the package, so the checksum verifies transport integrity and cannot detect an upstream
version change. RES has no pinned DCV version.

That is a deliberate trade: desktops pick up DCV fixes without a RES release. It is also an unmanaged
coupling. A DCV release that changes packaging, a configuration file location, or a service name can
break VDI bootstrap with no RES change involved. Amazon DCV remains a supported product independent of
RES, so this endpoint isn't going away when RES support ends. The risk is compatibility drift, not
disappearance.

**Mirroring.** You can mirror the packages you need to a bucket you control and rewrite the URLs in
`package_config.yml`. Mirroring specific package files under your own names also pins the version.
Check the DCV license terms for
redistribution before mirroring outside your own organization.

---

## 7. The rest of the VDI bootstrap fetches

Everything in this section happens at **instance launch**, not at install. **A RES environment that has
not changed in a year still makes all of these requests, from scratch, every time it boots a
desktop.** The fourteen entries below exclude the DCV packages, which are covered in §6 and are also
fetched at every launch.

| Endpoint | What it provides | Condition |
|---|---|---|
| `dl.fedoraproject.org/pub/epel/epel-release-latest-{8,9}.noarch.rpm` | EPEL repository definition | RHEL 8, RHEL 9, Rocky 9 |
| `fsx-lustre-client-repo.s3.amazonaws.com`, `fsx-lustre-client-repo-public-keys.s3.amazonaws.com` | FSx for Lustre client packages and signing keys | Any host mounting Lustre |
| `repo.radeon.com/amdgpu-install/6.2.1/ubuntu/jammy/...` | AMD GPU driver installer, version-pinned | AMD GPU instance types on Ubuntu 22.04 |
| `us.download.nvidia.com/tesla/<version>/...` | NVIDIA Tesla driver | NVIDIA GPU instance types |
| `github.com/pyenv/pyenv` via `https://pyenv.run` | pyenv, then Python built from source | Every Linux VDI |
| `github.com/aws/efs-utils` | EFS mount helper, cloned and built | Every Linux VDI mounting EFS |
| `github.com/mikefarah/yq/releases/latest/...` | `yq`, used by bootstrap scripts to read configuration | Every Linux VDI |
| `sh.rustup.rs` | Rust toolchain, needed to build efs-utils from source on some OSes | Conditional, in the efs-utils path |
| `rpmfind.net/.../pcsc-lite-libs-2.0.0-2.fc39.x86_64.rpm` | A single Fedora package, pulled directly from a community mirror to satisfy a DCV server dependency on Red Hat | RHEL DCV server install |
| `awscli.amazonaws.com/awscli-exe-linux-{x86_64,aarch64}.zip` | AWS CLI v2 | Every Linux host |
| `s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/...` | SSM agent | Hosts where it is not preinstalled |
| `s3.<region>.amazonaws.com/amazoncloudwatch-agent-<region>/...` | CloudWatch agent | Every host |
| `s3.amazonaws.com/mountpoint-s3-release/latest/...` | mountpoint-s3 | Hosts with S3 mounts |
| `www.pool.ntp.org` | Time synchronization | Every host |

`[verified]` The EPEL 9, FSx Lustre RHEL 9, `repo.radeon.com` and `pyenv.run` URLs and the
`github.com/aws/efs-utils` repository all returned 200 on 2026-09-05.

Note `rpmfind.net`. It is a community RPM mirror with no availability commitment and no relationship
to AWS, reached to fetch one Fedora `pcsc-lite-libs` package to satisfy a DCV dependency on Red Hat.
Vendor this one first.

Note also how many of these say `latest`. Six of the fourteen entries above resolve `latest` rather than
a pinned version: the SSM agent, the CloudWatch agent, mountpoint-s3, the AWS CLI, `yq` and EPEL. So
does every DCV package in §6. All of them resolve fresh on every boot.

---

## 8. A failure that already happened

In September 2026, VDI bootstrap on **Ubuntu 22.04** started failing in some regions with:

```
fatal: could not read Username for 'https://github.com'
```

The cause was outside RES entirely: GitHub sunset SHA-1 in its HTTPS stack, and the `git` version
shipped with Ubuntu 22.04 could no longer clone over HTTPS as a result. Both pyenv and efs-utils are
cloned from GitHub during bootstrap, so neither Python nor the EFS mount helper installed, and
`supervisord` never started. Desktops on that OS did not come up. The fix was a bootstrap change to
force HTTP/1.1 for git on that OS.

Three things about it, because a similar failure can recur:

**Nothing about RES changed.** No release, no configuration, no customer action. A third party
changed a TLS policy and a supported operating system stopped working.

**It was regional and OS-specific**, which is hard to diagnose. It presented as "Ubuntu
22.04 desktops fail in some regions", which looks like a RES defect or a capacity problem and does
not look like an upstream TLS change.

**It was caught because integration tests were running and someone was reading the results.** After
support ends that becomes the operator's job. §7 lists fourteen endpoints fetched at every launch, six
of which resolve `latest` rather than a pinned version, and §6 adds the DCV package set, which is also
unpinned.

The mitigation that survives handoff is **reducing the number of things fetched at launch at all**:
mirror what you can, pin what you cannot, and prefer a private mirror you control over an upstream you
do not. The section below lists what to mirror.

`[verified]` `supervisord` being active is the specific negative check on this failure mode. It was
confirmed active on the reference environment's desktop, alongside a working DCV console session.
Include `systemctl is-active supervisord` in any VDI health check you write.

---

## 9. Restricted networks: what to allowlist or mirror

If your VDI subnets have no general egress, this is the list, grouped by what needs each entry.

**Must have, or nothing launches.**

- `d1uj6qtbmh3dt5.cloudfront.net`: DCV
- `awscli.amazonaws.com`
- `s3.<region>.amazonaws.com` and `s3.amazonaws.com`: SSM agent, CloudWatch agent, mountpoint-s3
- Your own S3 staging bucket, reachable via a VPC endpoint: host modules and installation scripts
- `github.com` and `codeload.github.com`: pyenv, efs-utils, yq
- `pyenv.run`
- `www.pool.ntp.org`, or your own NTP source

**Per OS.**

- `dl.fedoraproject.org`: RHEL and Rocky
- Your distribution's own package mirrors, which are outside RES's control and OS-specific
- `sh.rustup.rs`: where efs-utils is built from source
- `rpmfind.net`: RHEL DCV server

**Per instance type.**

- `us.download.nvidia.com`: NVIDIA GPU
- `repo.radeon.com`: AMD GPU

**Per filesystem.**

- `fsx-lustre-client-repo.s3.amazonaws.com` and `fsx-lustre-client-repo-public-keys.s3.amazonaws.com`

**Only if you use the demo prerequisites in `samples/`.**

- `bootstrap.pypa.io/pip/3.7/get-pip.py`: `[verified]` returned 200; fetched by
  `samples/batteries-included/public-certs.yaml`. Note the `pip/3.7` path: this is the legacy pip
  bootstrap for Python 3.7, kept alive by PyPA for old interpreters, and it will be retired eventually.
- `github.com/acmesh-official/acme.sh/archive/refs/tags/3.1.0.tar.gz`: `[verified]` returned 200;
  the same template downloads and runs `acme.sh` to issue a Let's Encrypt certificate, so it also
  needs to reach Let's Encrypt's ACME endpoints and to write DNS-01 validation records.

  Why the template uses `acme.sh` rather than ACM: the DCV connection gateway terminates TLS itself,
  so it needs the certificate **and its private key**. ACM never releases a private key. Any path to a VDI
  certificate therefore involves a certificate authority you hold the key for. In production, use
  your own PKI and put the certificate and key in Secrets Manager; the `acme.sh` route is a
  convenience for demonstrating with a real domain name.

**RES itself needs, in addition,** the AWS service endpoints for the services it uses. Prefer VPC
endpoints for S3, DynamoDB, Secrets Manager, SSM, ECR and CloudWatch over NAT egress.

RES also accepts `HttpProxy`, `HttpsProxy` and `NoProxy` install parameters for isolated
deployments. `[inferred]` Whether every bootstrap fetch honors them is unconfirmed; several of the
downloads in §7 use tools that read the standard proxy environment variables, and some are `aws s3
cp`, which does. Test this before relying on it.

---

## 10. Build-time only

Two references matter only if you build or release RES, and neither should survive into a community
release process.

**`s3://solutions-build-assets/changelog-spec.yml`.** `[from source]` `buildspec.yml` fetches this
into `./buildspec.yml` in its `post_build` phase, replacing the build spec for a later stage. The
bucket is not publicly readable, so this line fails outside the AWS build environment. Delete the line;
maintain `CHANGELOG.md` by hand.

**`https://s3.amazonaws.com/viperlight-scanner/latest/viperlight.zip`.** Downloaded by the
`viperlight_scan` tox environment. The scanner is not available outside the AWS build environment, so
remove that environment and use an open equivalent. `bandit` is already wired up in `tox.ini`, and
`semgrep` or `trivy` cover similar ground.

Also inert: `sonar-project.properties` is referenced by nothing in the repository.

---

## 11. Deciding whether a published vulnerability affects RES

After AWS support ends, triaging third-party vulnerabilities against RES becomes the operator's work,
and it arrives as a steady stream rather than as an event.

The question is always the same. A vulnerability is published against some package. Does RES ship it,
and if so at a version inside the affected range?

### 11.1 Where RES declares what it depends on

`[verified]` Four declaration sets, and a fifth thing that is not a declaration at all:

| Layer | Where to look | Count on 2026.09 |
|---|---|---|
| Python, resolved | `requirements/*.txt`, which are compiled from the matching `.in` files | 15 groups |
| Python, per module | `setup.py` in each module under `source/idea/*/src/` | 12 files |
| Web portal | `source/idea/idea-cluster-manager/webapp/package.json`, with `yarn.lock` for what actually resolves | 1 |
| Host modules | `source/infra/host_modules/go.mod` and `go.sum` | 1 |
| Operating system | **Not declared anywhere.** See below | |

Search the resolved files rather than the `.in` files: a vulnerability in a transitive dependency will
appear only in the compiled `.txt`, and in `yarn.lock` rather than `package.json`.

**The operating-system layer is the gap.** What is installed on a running desktop comes from the base
AMI plus whatever the bootstrap scripts install at launch, and no manifest exists for the result. To
answer an OS-level question you have to read
`source/idea/idea-bootstrap/resources/scripts/common/linux/` for what gets installed, and then query a
running instance for what is actually present. §7 lists the bootstrap fetches; a package installed from
a distribution repository is whatever that repository served on the day the desktop launched, which also
means two desktops from the same software stack can differ.

### 11.2 The method

1. **Read the advisory from its own source**, not from a summary. Summaries in a ticket or a scanner
   report are frequently stale about affected version ranges, which is the field the verdict turns on.
2. **Find the package in the right declaration set** from §11.1, matching the ecosystem rather than the
   name alone.
3. **Compare the pinned version against the affected range.** Read the pin; do not recall it. RES pins
   in several places and they do not always agree; Python in particular is pinned in several files that
   can disagree.
4. **Record a verdict, and record the check that produced it.** Four verdicts cover the cases:
   **likely impacted**, **possibly impacted**, **not impacted**, and **needs investigation**.

**Say which check ruled the vulnerability out.** A "not impacted" verdict without one is not worth
keeping. Two arguments recur. The first is that RES pins the package outside the affected range, which
you can check from the repository. The second is that the attack requires access a RES deployment does
not grant to the attacker in question, which depends on a threat model for your own deployment. Record
the second as a judgment, not as a fact.

### 11.3 Rules that keep a verdict trustworthy

- **Read the pin, do not recall it.** It's in the repository and takes a minute to check.
- **Read the advisory at source.** Summaries and affected ranges drift; the authoritative record does not.
- **Record the check that produced the verdict.** A "not impacted" with no reason has to be answered
  again six months later.
