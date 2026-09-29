# RES samples

CloudFormation templates that stand up the prerequisite resources for a **demonstration or
evaluation** deployment of Research and Engineering Studio.

## What these are, and what they are not

These are demo-grade templates. They come from a recipe named `res_demo_env` in
[aws-samples/aws-hpc-recipes](https://github.com/aws-samples/aws-hpc-recipes), and they build a
demonstration environment: a demonstration AWS Managed Microsoft AD populated from a fixed LDIF
file, a demonstration VPC, a demonstration EFS file system, and, optionally, certificates
issued by Let's Encrypt at deploy time.

They are **not** supported product components, and they are not a production prerequisite path.
A production deployer brings their own directory service, their own Cognito user pool, their own
network and their own file system, and passes those to the RES installation directly. Nothing in
`samples/` is required to install RES.

Two consequences:

- The Active Directory these templates create is seeded from `batteries-included/res.ldif`, a fixed file
  of demonstration users, groups and organizational units. The structure is public, in this repository,
  and identical in every deployment, so do not attach a real user population to it. The users' passwords
  are not in that file; they come from the `UserPassword` stack parameter.
- **The directory administrator password reaches the management instance's EC2 user data in plaintext.**
  Supplying it as a Secrets Manager ARN does not change that, because `bi.yaml` resolves the ARN and
  passes the value through. Treat any credential given to these templates as demonstration-only: rotate
  it afterwards and do not reuse it anywhere else.
- `batteries-included/public-certs.yaml` issues a certificate with `acme.sh` against Let's
  Encrypt on an EC2 instance. It is a convenience for a demonstration with a real domain name,
  not a certificate management strategy.

## Why they are in this repository

They used to be fetched at deploy time from an S3 bucket backing a separately owned GitHub
repository. RES should not depend on a repository it does not own, so the closure was copied here
and the cross-repository references were rewritten to point inside this tree. Provenance is
recorded in `PROVENANCE.md` so the copy can be refreshed deliberately rather than drifting.

## Layout

```
samples/
  README.md
  PROVENANCE.md                 source commit and per-file checksums
  publish-samples.sh            uploads the tree and prints the values a deployment needs
  batteries-included/
    bi.yaml                     the parent template; the only one you launch
    demo-managed-ad.yaml
    demo-managed-ad-windows-host.yaml
    network-large-scale.yaml
    public-certs.yaml
    efs-simple.yaml
    res.ldif
    service_account.ps1
  res-ready-ami/
    nested-imagebuilder-components.yaml
    imagebuilder-infrastructure.yaml
    components/
      research-and-engineering-studio-vdi-linux.yaml
      research-and-engineering-studio-vdi-windows.yaml
```

## How to use them

Nested stacks are fetched by CloudFormation over HTTPS, so the templates have to be in an S3
bucket you control before you launch them.

### 1. Publish

```
./publish-samples.sh --bucket my-res-samples --prefix res-samples --region us-west-2
```

The script refuses to run if the tree is incomplete, then prints the three values you need:

```
bi.yaml URL, pass as BIStackTemplateURL to the RES installation:

  https://my-res-samples.s3.us-west-2.amazonaws.com/res-samples/batteries-included/bi.yaml

bi.yaml parameters:

  SamplesS3Base   https://my-res-samples.s3.us-west-2.amazonaws.com/res-samples
  SamplesS3Path   my-res-samples/res-samples
```

`SamplesS3Base` is the HTTPS base URL, used for the nested `TemplateURL` values.
`SamplesS3Path` is the same location in `bucket/prefix` form, used for the two data files, which
the child templates fetch as `bucket/key` strings rather than URLs.

### 2. Launch

Either deploy `bi.yaml` yourself and feed its outputs to the RES installation, or let the RES CDK
application deploy it for you:

```
cdk deploy \
  -c batteries_included=true \
  -c BIStackTemplateURL=https://my-res-samples.s3.us-west-2.amazonaws.com/res-samples/batteries-included/bi.yaml \
  -c SamplesS3Base=https://my-res-samples.s3.us-west-2.amazonaws.com/res-samples \
  -c SamplesS3Path=my-res-samples/res-samples \
  ...
```

Set `CreateActiveDirectory=True`. See "Defaults and behaviors to check" below.

`SamplesS3Base` and `SamplesS3Path` have no defaults, because there is no location that could be
right for every deployer. `BiStack` in `source/idea/batteries_included/stack.py` passes a fixed
set of parameters to this template and must forward these two as well:

```python
"SamplesS3Base": str(self.node.try_get_context("SamplesS3Base")),
"SamplesS3Path": str(self.node.try_get_context("SamplesS3Path")),
```

If you deploy `bi.yaml` directly with `aws cloudformation deploy` rather than through the CDK
application, supply both on the command line and no code change is involved.

### RES-ready AMIs

`res-ready-ami/` is independent of `batteries-included/` and is used when you want to bake RES's
VDI dependencies into an AMI with EC2 Image Builder. Launch
`res-ready-ami/nested-imagebuilder-components.yaml` with the same `SamplesS3Base` value, then
`res-ready-ami/imagebuilder-infrastructure.yaml`.

## What each template does

**`batteries-included/bi.yaml`** is the parent. It creates nothing directly except three
CloudFormation custom resources: one resolves passwords supplied either literally or as
Secrets Manager ARNs, one finds the Route 53 hosted zone for a portal domain name, and one opens NFS
ingress on the EFS mount target security group. There is also an ACM certificate when a portal domain
name is given. Everything else is a nested stack. Its outputs are the values the
RES installation consumes.

**`batteries-included/network-large-scale.yaml`** creates a VPC with public and private subnets
across two or three Availability Zones, NAT gateways, route tables and VPC endpoints. RES uses
the public subnets for the load balancer and the private subnets for infrastructure hosts and
virtual desktops.

**`batteries-included/demo-managed-ad.yaml`** creates an AWS Managed Microsoft AD directory, a
service account, a Secrets Manager secret holding the service account credentials, and a Linux
management instance that loads `res.ldif` into the directory to create the demonstration OU
structure, users and groups.

**`batteries-included/demo-managed-ad-windows-host.yaml`** launches a domain-joined Windows
management instance and runs `service_account.ps1` on it to delegate the permissions the RES
service account needs to create computer objects. It exists because those delegations cannot be
made through the AWS API.

**`batteries-included/efs-simple.yaml`** creates an encrypted EFS file system with mount targets
in each private subnet, plus a client security group. RES uses it as the shared home directory.

**`batteries-included/public-certs.yaml`** launches a short-lived instance that runs `acme.sh`
against Let's Encrypt to obtain a certificate and private key for a domain in a Route 53 hosted
zone in the same account, and stores both in Secrets Manager. RES needs the private key, not just
a certificate, because the DCV connection gateway terminates TLS itself and ACM never releases a
private key. Only runs when `PortalDomainName` is set.

**`batteries-included/res.ldif`** is the demonstration directory content: the RES OU structure and
a small set of users and groups.

**`batteries-included/service_account.ps1`** is the delegation script run by the Windows
management host.

**`res-ready-ami/nested-imagebuilder-components.yaml`** creates the two EC2 Image Builder
components, Linux and Windows, that install the RES virtual desktop dependencies during an image
build.

**`res-ready-ami/imagebuilder-infrastructure.yaml`** creates the Image Builder infrastructure
configuration for a RES environment: a security group, an instance profile, and the IAM role that
lets the build instance read the RES environment's configuration and installation packages.

## What was changed relative to upstream

Eight of the twelve files are byte-identical to upstream. Four were rewritten: two to remove
cross-repository references, and two to fix security defects found by a pre-publication review of this
tree. `PROVENANCE.md` records a SHA-256 for every file, so a changed file is detectable.

**`batteries-included/bi.yaml`**

- Two parameters added, `SamplesS3Base` and `SamplesS3Path`.
- Five nested `TemplateURL` values now resolve against `SamplesS3Base`.
- `PSS3Path` now resolves against `SamplesS3Path`.
- `LDIFS3Path` previously defaulted to a path in the upstream bucket. A CloudFormation parameter
  default cannot contain an intrinsic function, so it could not simply be rewritten to a `!Sub`.
  It now defaults to the empty string, and a new condition, `LDIFSuppliedByUser`, selects the
  vendored `res.ldif` when the parameter is left empty. Supplying your own LDIF path still works
  exactly as before.
- `PSS3PathRegion` was hardcoded to `us-east-1`, or `us-gov-west-1` in GovCloud. That branch
  existed only to pick between the two regional copies of the upstream bucket. Once the file is
  served from the deployer's own bucket the correct value is the region that bucket is in, which
  for a bucket published by `publish-samples.sh` in the deploying region is `AWS::Region`. So it
  is now `!Ref AWS::Region`, which is right in every partition including GovCloud, and the
  `InGovCloud` condition, retained since it may be useful again, is now unused. A deployer who
  publishes the samples to a bucket in a different region from the RES deployment must set
  `PSS3PathRegion` explicitly.

**`res-ready-ami/nested-imagebuilder-components.yaml`**

- The `HpcRecipesS3Bucket` and `HpcRecipesBranch` parameters are replaced by `SamplesS3Base`, and
  the two nested `TemplateURL` values resolve against it.

**`batteries-included/public-certs.yaml`**, hardened relative to upstream.

- The certificate host's instance role is scoped to the permissions its user data actually uses:
  `cloudformation:DescribeStackResource` and `cloudformation:SignalResource` on this stack, for
  `cfn-init` and `cfn-signal`; `route53:ListHostedZones`, `route53:GetChange` and
  `route53:ListResourceRecordSets`, which `acme.sh` needs to find the zone and poll the change; and
  `secretsmanager:PutSecretValue` scoped to the two secrets.
- The `route53:ChangeResourceRecordSets` grant is conditioned with `StringLike` on
  `_acme-challenge.*` and allows `CREATE`, `DELETE` and `UPSERT`, which are the operations `acme.sh`
  performs.
- `HttpPutResponseHopLimit` is 1, so instance credentials are not reachable from a container or proxy
  on the instance.
- **Verified by deployment.** This template was deployed with `PortalDomainName` set against a
  delegated public hosted zone: both TXT challenges were written and validated, a Let's Encrypt
  certificate was issued for the domain and its wildcard, both secrets were populated, `cfn-signal`
  returned, the stack reached `CREATE_COMPLETE`, and the instance log recorded no access denials.

**`batteries-included/demo-managed-ad.yaml`**, hardened relative to upstream.

- The directory administrator password is written to a mode-600 temporary file and passed to
  `ldapmodify` with `-y`, then removed, rather than given on the command line. `realm join` and `adcli`
  already took it on standard input.
- This does not remove the password from the instance's user data, which is inherent to how `bi.yaml`
  supplies it. See the warning above.

All four rewritten files begin with a four-line provenance comment. The other eight have none,
so that they remain byte-identical to upstream and the copy stays mechanically verifiable;
`PROVENANCE.md` records their origin and checksums instead.

## Provenance and license

Source: `https://github.com/aws-samples/aws-hpc-recipes`, commit and date recorded in
`PROVENANCE.md`.

Upstream license: **MIT No Attribution (MIT-0)**. It permits use, modification and redistribution
with no attribution or notice requirement, so no `NOTICE` entry is needed. Two of the twelve files
carry an Apache-2.0 notice inside their Image Builder component content, which is the same license as
this repository and is preserved as part of the file; `PROVENANCE.md` records which. Provenance is
recorded for the benefit of whoever next has to update these files, not for compliance.

## Runtime dependencies that vendoring does not remove

Copying these templates into this repository removes the dependency on the upstream repository. It
does not remove what the templates reach out to while they are running. A deployer on a restricted
network needs to know about all of these.

**Third party:**

- `https://bootstrap.pypa.io/pip/3.7/get-pip.py`, a `get-pip` bootstrap pinned to a
  path for Python 3.7, which is end of life. Fetched twice in
  `batteries-included/public-certs.yaml`.
- `https://github.com/acmesh-official/acme.sh/archive/refs/tags/$VERSION.tar.gz`, a third-party
  ACME client, fetched as a release tarball in `batteries-included/public-certs.yaml`. This is in
  the path that issues certificates.

**AWS-owned, in the RES-ready AMI path:**

- `s3://research-engineering-studio-us-east-1/releases/latest/res-installation-scripts.tar.gz`:
  both Image Builder components download the RES installation scripts from the RES release bucket,
  and from `us-east-1` specifically, regardless of the build region. If you build your own
  installation scripts you must edit these two component templates to point at your own bucket.
- `res-ready-ami/imagebuilder-infrastructure.yaml` grants the build instance read access to
  `research-engineering-studio-${AWS::Region}/host_modules/*` and to the AWS-owned DCV license,
  NVIDIA and AMD driver buckets.

The templates also install packages from the distribution repositories of Amazon Linux and
Windows Server in the usual way.

## Defaults and behaviors to check

**`EnvironmentName` defaults to `res-demo`.** Reusing it in a region where a `res-demo`
environment previously existed collides with whatever that deployment left behind: DynamoDB
tables named `res-demo.cluster-settings` and `res-demo.modules` in particular survive stack
deletion. Choose a distinct name.

**`CreateActiveDirectory` defaults to `False`.** Left at the default, `bi.yaml` creates no
directory, emits none of the directory-related outputs, and RES has nothing to bind to. If you
want the demonstration directory, set it to `True`, and then `DomainName`, `AdminPassword`,
`ServiceAccountPassword` and `Keypair` all become required.

**`ClientIpCidr` defaults to empty**, which creates no SSH ingress rule on the directory management
instances. It does not control access to the RES portal; the RES install parameter `ClientIp` does.

**`bi.yaml` emits no Cognito outputs.** RES needs a `CognitoUserPoolId`; passing an empty string
makes the RES identity stack create its own pool. These templates do not create one.

**Deleting the stack does not delete everything.** `RetainStorageResources` defaults to `True`,
which sets a `Retain` deletion policy on the VPC and the EFS file system. That is deliberate, and it
means a delete leaves resources, and cost, behind.
