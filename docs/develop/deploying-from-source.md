# Deploying RES from Source to a Personal CodePipeline

This guide walks you through building and deploying Research and Engineering Studio on AWS (RES) from source, in your own AWS development account, using an [AWS CodePipeline](https://aws.amazon.com/codepipeline/) that builds directly from your source code.

Use this when you want to test unreleased / source-based changes end to end, rather than installing a released version from the public template.

> **Note:** For standard RES deployments and full product documentation, see the official [RES User Guide](https://docs.aws.amazon.com/res/latest/ug/) (or the Related documentation section).

> **Warning:** Personal development only. This workflow is intended for a developer's own non-production AWS account. It provisions billable resources (VPC endpoints, EC2, load balancers, ECR, S3, etc.).

## How it works

Instead of deploying a prebuilt RES template, you:

- Push the RES source into a CodeCommit repository in your dev account.
- Deploy two CDK "pipeline" stacks that create CodePipelines wired to that repo:

  - RESBuildPipelineStack — builds RES, then deploys the RES environment stack (Deploy-ResearchAndEngineeringStudio) and runs integration tests.
  - RESHostModulesPipelineStack — builds and publishes the host modules (the software installed on RES hosts) to an S3 bucket you own.
- Every push to your CodeCommit branch triggers the build pipeline, giving you a full source-to-environment loop.

> **(Optional)** If instead of deploying directly you want the pipeline to **generate a reusable install template and artifacts into buckets/ECR you own** — so the template can be handed to others and deployed into any account/Region — see *Publishing templates and host modules to your own buckets (self-hosted distribution)* near the end of this guide. That path builds on the same Steps 1–7 but replaces Steps 8–9 with publish-mode variants.

## Prerequisites

There are three prerequisites: an AWS account, external resources, and local tooling.

### 1. AWS account

- A personal / non-production AWS account you have administrative access to.
- Credentials configured locally so the AWS CLI and CDK can call your account. Please check the [public AWS doc for configuring credentials for CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html).

Verify:

```
aws sts get-caller-identity
```

### 2. External resources

External resources are required. RES cannot deploy without a VPC, subnets, an Active Directory, and shared storage (EFS) to deploy into. You must provide these in one of three ways:

- **Pre-provisioned (bring-your-own).** Use an existing VPC/AD/EFS you already operate. You read the resource identifiers into your CDK context (~/.cdk.json) (Step 5, Option A).
- **Deploy the external-resources template yourself (recommended)**. If you do not have the resources, deploy the RES demo external-resources CloudFormation template ([bi.yaml](https://s3.amazonaws.com/aws-hpc-recipes/main/recipes/res/res_demo_env/assets/bi.yaml)) as a standalone stack first — see [Create external resources](https://docs.aws.amazon.com/res/latest/ug/create-external-resources.html) in the RES Installation guide. Then read its Outputs into your CDK context (~/.cdk.json) (Step 5, Option A) — from RES's perspective this is still bring-your-own.
- **Deploy the external-resource template through pipeline (batteries_included=true)**. Let the pipeline provision them for you — it deploys a external resource stack (from the same bi.yaml) before the RES environment stack and passes the values through SSM. You configure SSM parameter paths instead of literal resource IDs. This path requires a custom domain — you must provide a public domain as PortalDomainName (External resource stack cannot self-sign the certificate). See Step 5, Option B.

> **Tip:** Updating the external resource stack with custom domain frequently via pipeline may cause throttling from Let's Encrypt.

> The difference between options 2 and 3: in option 2 you deploy bi.yaml as a separate step and hand RES the literal outputs; in option 3 the pipeline deploys bi.yaml for you as part of the RES deploy and wires the values via SSM. Both use the same template.

We recommend option 2 for most deployments — it uses Option A in Step 5 and Step 8. Choose deploy the external-resource template through pipeline (option 3, Option B in Step 5 and Step 8) only if you want the pipeline to provision everything and you have a public domain to use as PortalDomainName. Follow the matching Option A / Option B guidance in Step 5 and Step 8.

### 3. Tooling

Because the pipeline runs the heavy build steps (web portal, container images, packaging) in AWS, you only need a small local toolset:

| Tool | Version | Notes |
| --- | --- | --- |
| [Python](https://www.python.org/downloads/) | 3.12.11 (2026.03 and later) or 3.9.16 (2025.12.01 and earlier) | Version depends on your checkout's requires-python — see Step 2. Install from [python.org/downloads](https://www.python.org/downloads/) (or Homebrew/apt/pyenv). |
| [Node.js](https://nodejs.org/) | 20.19.0 (2026.06 and later) or 18.18.0 (2026.03 and earlier)    | Only to run the AWS CDK CLI via npx. |
| [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) | latest | For account and CodePipeline commands. |
| [git](https://git-scm.com/) | latest | To clone and push source. |

> Throughout this guide, replace <region> with your target AWS Region (for example us-east-1) and <account-id> with your 12-digit AWS account ID.

## Deployment steps

### Step 1 — Clone the source

Clone the public RES repository from GitHub:

```
git clone https://github.com/aws/res.git
cd res
```

The default branch is mainline. This guide uses a working branch named develop, because develop is the default branch the pipelines watch. Create it from whatever commit you want to test:

```
git checkout -b develop
```

> **Note:** You can create this branch from any commit or release tag you want to test, but flags and options vary by RES version — not everything in this guide exists on older releases (for example, the nightly-test-suite flags are 2026.09+). This guide targets RES 2026.06 and newer.

### Step 2 — Set up your Python environment

The required Python version depends on which RES version you checked out:

- 2026.03 and later: Python 3.12 (>=3.12.0)
- 2025.12.01 and earlier: Python 3.9 (>=3.9.16,<3.10)

The authoritative value is the requires-python field in pyproject.toml for your checkout. Confirm it:

```
grep requires-python pyproject.toml
```

Installing with a version outside that range fails with Package 'idea' requires a different Python. Substitute the matching version (3.12 or 3.9) in the commands below.

Check whether you already have the right interpreter (example for 3.12):

```
python3.12 --version   # or: python3.9 --version
```

If it is not installed, see the [official Python installation guide](https://wiki.python.org/moin/BeginnersGuide/Download) for your platform.

Create and activate a virtual environment using the matching interpreter:

```
# Using your system Python (3.12 shown; use python3.9 for older versions):
python3.12 -m venv venv

# Or, if you manage versions with pyenv:
# ~/.pyenv/versions/3.12.0/bin/python3 -m venv venv
# (older versions: ~/.pyenv/versions/3.9.16/bin/python3 -m venv venv)
```

Activate it and install the development dependencies:

> Tip: These environment variables only apply to the current shell session. You need to re-export them (and re-activate the venv) each time you open a new terminal. To make them persistent, add the export lines to your shell profile (e.g. ~/.bashrc, ~/.zshrc) or a .env file you source before working on RES

```
export SKIP_ENV_UPDATE=true
export RES_DEV_MODE=true
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements/dev.txt
```

> Minor dependency-resolution conflict warnings during install can generally be ignored.

### Step 3 — Build the libraries

Build the shared RES libraries and the data model before running any CDK command:

```
invoke clean.library build.library package.library
invoke clean.datamodel build.datamodel package.datamodel
```

If you plan to build and test the components locally, you can also build them (optional — the pipeline builds them for you):

```
invoke clean.cluster-manager build.cluster-manager package.cluster-manager
invoke clean.virtual-desktop-controller build.virtual-desktop-controller package.virtual-desktop-controller
invoke clean.virtual-desktop build.virtual-desktop package.virtual-desktop
```

### Step 4 — Create a CodeCommit repository

The pipelines pull source from a CodeCommit repository in your account. The default repository name the pipelines expect is DigitalEngineeringPlatform.

Create it:

```
aws codecommit create-repository --repository-name DigitalEngineeringPlatform --region <region>
```

Confirm it exists:

```
aws codecommit get-repository --repository-name DigitalEngineeringPlatform --region <region> --query "repositoryMetadata.Arn" --output text
```

> **Tip:** You can also create the repository in the console: open the [CodeCommit console](https://console.aws.amazon.com/codesuite/codecommit/repositories) in your target Region, choose Create repository, and name it DigitalEngineeringPlatform.

### Step 5 — Configure deployment context

RES reads its deployment parameters from CDK context, which you provide in ~/.cdk.json (see below). The exact keys depend on which external-resources path you chose in Prerequisites:

- Option A — Bring-your-own (pre-provisioned). You supply the literal VPC/subnet/AD/EFS identifiers. This is the default path.
- Option B — External resource stack. RES provisions the external resources; you supply SSM parameter paths (not literal IDs) plus batteries_included settings.

In both cases, put the values in ~/.cdk.json (your home directory) under a top-level "context": { ... } key. This file is per-user and never committed, so account-specific values (passwords, IPs, ARNs) stay out of the repo (you can use cdk.json in the repo root instead, but only for non-sensitive values). Each scalar value is a JSON-escaped string (e.g. "ADShortName": ""CORP""); leave optional fields as """". See the [AWS CDK context guide](https://docs.aws.amazon.com/cdk/v2/guide/context.html) for details.

> What each parameter means: these are the same RES parameters you'd set in the CloudFormation console (EnvironmentName, ClientIp, VpcId, the AD / subnet / OU fields, the cert ARNs, Cognito, etc.) — just supplied via CDK context here. For a full description of every parameter, see the public [RES "Launch the product" parameter table](https://docs.aws.amazon.com/res/latest/ug/launch-the-product.html).

> **Tip:** You can still override or add individual values on the command line with -c KEY=VALUE, which takes precedence over any file.

> **Important:** Set ClientIp carefully — it controls who can reach your RES web portal and bastion host. Use a specific CIDR (your own IP as 203.0.113.10/32, or a range like 203.0.113.0/24); find your public IP with curl -s https://checkip.amazonaws.com/. Never use 0.0.0.0/0 (exposes the environment to the entire internet). Alternatively set ClientPrefixList to a managed prefix list ID.

#### Option A — Bring-your-own (pre-provisioned external resources)

These values come from one of two sources, depending on how you provisioned your prerequisites:

- Your own infrastructure — an existing VPC, subnets, Active Directory, and EFS you already operate. Read the identifiers from wherever you manage them.
- The external-resources stack you deployed yourself (recommended) — read them from that stack's Outputs (via the CLI below or the CloudFormation console):

```
aws cloudformation describe-stacks \
  --stack-name <your-external-resources-stack> \
  --region <region> \
  --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" --output table
```

> **Tip:** You can also read these values from the CloudFormation console instead of the CLI: open the [CloudFormation console](https://console.aws.amazon.com/cloudformation/) in your target Region, select your external resources stack, and open the Outputs tab — each key/value pair listed there maps to the context values below.

Put the following in` ~/.cdk.json` (recommended) or `cdk.json`. In Option A, every VPC/subnet/AD/EFS value is a literal identifier that comes from your bring-your-own prerequisites — an existing VPC/AD/EFS you operate (Prerequisites option 1), or the Outputs of the external-resources stack you deployed yourself (Prerequisites option 2), read via the CLI/console above. Fill in the values for your environment (keep real ARNs, account IDs, and resource IDs in ~/.cdk.json so they are never committed to a public repo):

> See the [public RES "Launch the product" parameter table](https://docs.aws.amazon.com/res/latest/ug/deploy-the-product.html) for which parameters are required vs. optional.

```
{
  "context": {
    "ACMCertificateARNforWebApp": "\"\"",
    "ADShortName": "\"<ad-short-name>\"",
    "ActiveDirectoryName": "\"<fqdn, e.g. corp.example.com>\"",
    "AdministratorEmail": "\"you@example.com\"",
    "CertificateSecretARNforVDI": "\"\"",
    "ClientIp": "\"<your-cidr, e.g. 203.0.113.10/32>\"",
    "ClientPrefixList": "\"\"",
    "CognitoUserPoolDomainUrl": "\"\"",
    "CognitoUserPoolId": "\"\"",
    "ComputersOU": "\"<computers-ou>\"",
    "CustomDomainNameforVDI": "\"\"",
    "CustomDomainNameforWebApp": "\"\"",
    "DisableADJoin": "\"False\"",
    "DomainTLSCertificateSecretArn": "\"\"",
    "EnableLdapIDMapping": "\"True\"",
    "EnvironmentName": "\"res-dev\"",
    "GroupsOU": "\"<groups-ou>\"",
    "HttpProxy": "\"\"",
    "HttpsProxy": "\"\"",
    "IAMPermissionBoundary": "\"\"",
    "IAMResourcePath": "\"\"",
    "IAMResourcePrefix": "\"\"",
    "InfrastructureHostAMI": "\"\"",
    "InfrastructureHostSubnets": "[\"<private-subnet-a>\",\"<private-subnet-b>\"]",
    "IsLoadBalancerInternetFacing": "true",
    "LDAPBase": "\"<e.g. dc=corp,dc=example,dc=com>\"",
    "LDAPConnectionURI": "\"<e.g. ldap://corp.example.com>\"",
    "LoadBalancerSubnets": "[\"<public-subnet-a>\",\"<public-subnet-b>\"]",
    "NoProxy": "\"\"",
    "PrivateKeySecretARNforVDI": "\"\"",
    "SSHKeyPair": "\"<your-ec2-keypair-name>\"",
    "ServiceAccountCredentialsSecretArn": "\"<secretsmanager-arn>\"",
    "ServiceAccountUserDN": "\"<service-account-dn>\"",
    "SharedHomeFileSystemId": "\"<efs-fs-id>\"",
    "SudoersGroupName": "\"<sudoers-group>\"",
    "UsersOU": "\"<users-ou>\"",
    "VdiSubnets": "[\"<private-subnet-a>\",\"<private-subnet-b>\"]",
    "VpcId": "\"<vpc-id>\""
  }
}
```

#### Option B — **Deploy the external-resource template through pipeline** (RES provisions the external resources)

With batteries_included=true, the pipeline deploys a BatteriesIncluded stack (VPC, subnets, AD, EFS) before the RES environment stack, writes the resulting identifiers into SSM parameters, and RES reads them back from SSM. So, the network/AD/storage keys hold SSM parameter paths (strings like /res-deploy/external/VpcId), not literal resource IDs. You still supply the literal "turnkey" inputs (environment name, admin email, keypair, client IP, and the AD ServiceAccountPassword).

> **Important:** Batteries Included uses a custom domain for the web portal. Set PortalDomainName to a public domain you own (in a Route 53 hosted zone in this account), along with CustomDomainNameforWebApp and CustomDomainNameforVDI. When set, the certificate is generated for you and written to the SSM parameters shown below — leave those cert-secret keys as the /res-deploy/external/... paths. If you don't set a domain, the deploy stage will fail.

The example below is the [RES demo-environment recipe](https://s3.amazonaws.com/aws-hpc-recipes/main/recipes/res/res_demo_env/assets/bi.yaml) form, using the same "context": { ... } wrapper as Option A — put it in ~/.cdk.json (recommended) or cdk.json.

> **Tip:** In Batteries Included you only fill in a few fields — the rest are fixed: the /res-deploy/external/... values are SSM parameter paths the BI stack populates (leave them as-is), and BIStackTemplateURL stays as shown. You set:

> EnvironmentName, AdministratorEmail, SSHKeyPair

> ClientIp (or ClientPrefixList)

> ServiceAccountPassword (the AD service-account password BI creates)

> Everything else can stay at the defaults shown; Optional fields can be left as empty escaped strings ("""").

```
{
  "context": {
    "EnvironmentName": "\"res-deploy\"",
    "AdministratorEmail": "\"<your-email, e.g. test@example.com>\"",
    "SSHKeyPair": "\"<name-of-ssh-key>\"",
    "ClientIp": "\"<your-cidr, e.g. 203.0.113.10/32>\"",
    "ClientPrefixList": "\"\"",
    "ServiceAccountPassword": "\"<choose-a-strong-password>\"",
    "ServiceAccountCredentialsSecretArn": "\"/res-deploy/external/ServiceAccountCredentialsSecretArn\"",
    "PortalDomainName": "\"<your-domain, e.g. res.example.com>\"",
    "CustomDomainNameforWebApp": "\"web.<your-domain>\"",
    "CustomDomainNameforVDI": "\"vdc.<your-domain>\"",
    "DomainTLSCertificateSecretArn": "\"\"",
    "DisableADJoin": "\"False\"",
    "VpcId": "\"/res-deploy/external/VpcId\"",
    "LoadBalancerSubnets": "\"/res-deploy/external/LoadBalancerSubnets\"",
    "InfrastructureHostSubnets": "\"/res-deploy/external/InfrastructureHostSubnets\"",
    "VdiSubnets": "\"/res-deploy/external/VdiSubnets\"",
    "IsLoadBalancerInternetFacing": "\"true\"",
    "ActiveDirectoryName": "\"/res-deploy/external/ActiveDirectoryName\"",
    "LDAPBase": "\"/res-deploy/external/LDAPBase\"",
    "ADShortName": "\"/res-deploy/external/ADShortName\"",
    "LDAPConnectionURI": "\"/res-deploy/external/LDAPConnectionURI\"",
    "EnableLdapIDMapping": "\"True\"",
    "InfrastructureHostAMI": "\"\"",
    "UsersOU": "\"/res-deploy/external/UsersOU\"",
    "GroupsOU": "\"/res-deploy/external/GroupsOU\"",
    "ComputersOU": "\"/res-deploy/external/ComputersOU\"",
    "SudoersGroupName": "\"/res-deploy/external/SudoersGroupName\"",
    "SharedHomeFileSystemId": "\"/res-deploy/external/SharedHomeFileSystemId\"",
    "ACMCertificateARNforWebApp": "\"/res-deploy/external/ACMCertificateARNforWebApp\"",
    "CertificateSecretARNforVDI": "\"/res-deploy/external/CertificateSecretARNforVDI\"",
    "PrivateKeySecretARNforVDI": "\"/res-deploy/external/PrivateKeySecretARNforVDI\"",
    "IAMPermissionBoundary": "\"\"",
    "HttpProxy": "\"\"",
    "HttpsProxy": "\"\"",
    "NoProxy": "\"\"",
    "IAMResourcePrefix": "\"\"",
    "IAMResourcePath": "\"\"",
    "BIStackTemplateURL": "https://s3.amazonaws.com/aws-hpc-recipes/main/recipes/res/res_demo_env/assets/bi.yaml",
    "ServiceAccountUserDN": "\"/res-deploy/external/ServiceAccountUserDN\"",
    "RetainStorageResources": "\"False\"",
    "CognitoUserPoolId": "\"\"",
    "CognitoUserPoolDomainUrl": "\"\""
  }
}
```

> **Note:**

> BIStackTemplateURL is the RESExternal/bi.yaml template that provisions the VPC/AD/EFS. The demo-environment value is shown above; it can also be passed on the deploy command in Step 8.

> The SSM path strings (the /res-deploy/external/... names) can follow any consistent convention — RES writes to and reads from whatever paths you specify.

Field reference. The [RES "Launch the product" parameter table](https://docs.aws.amazon.com/res/latest/ug/launch-the-product.html) (linked above) describes every parameter; the authoritative key list lives in the parameter classes under source/idea/infrastructure/install/parameters/ (and .../batteries_included/parameters/) and can evolve with the source. A few format rules specific to this guide:

- EnvironmentName — starts with res-, lowercase, ≤ 11 characters (e.g. res-dev1).
- Subnet keys (LoadBalancerSubnets, InfrastructureHostSubnets, VdiSubnets) — Option A: JSON arrays of subnet IDs (≥2 in different AZs); Option B: SSM path strings. Public subnets for an internet-facing load balancer; private subnets for infra hosts and VDIs.
- SharedHomeFileSystemId — Option A: an EFS ID (fs-...); Option B: an SSM path.
- ServiceAccountCredentialsSecretArn — Option A: a Secrets Manager ARN (username:password); Option B: an SSM path (BI creates the secret).
- EnableLdapIDMapping / DisableADJoin — "True" or "False".
- IsLoadBalancerInternetFacing — true/false. Option A uses the bare form ("true"); the Option B recipe shows it JSON-escaped (""true""). If a deploy rejects the escaped form, switch to the bare "true".

#### Isolated / private-VPC deployments

*(Advanced — skip for a standard internet-connected deploy.)*

Deploying into a VPC without internet access needs extra setup (VPC endpoints, a proxy for services without endpoints, and a prebaked `InfrastructureHostAMI`), and several parameters change:

- `IsLoadBalancerInternetFacing` → false
- `LoadBalancerSubnets` / `InfrastructureHostSubnets` / `VdiSubnets` → private subnets without internet access
- `ClientIp` → your VPC CIDR
- `InfrastructureHostAMI` → the AMI you prebaked with the RES install scripts
- `HttpProxy` / `HttpsProxy` / `NoProxy` → your proxy server and no-proxy list

Follow the public [Prerequisites → Configure a private VPC](https://docs.aws.amazon.com/res/latest/ug/prerequisites.html#private-vpc) guide and the [Set private VPC deployment parameters](https://docs.aws.amazon.com/res/latest/ug/prerequisites.html#vpc-deployment-parameters) table (which also documents `HttpProxy` / `HttpsProxy` / `NoProxy`). `PortalDomainName` belongs to the custom-domain setup. All of these can be left empty for a standard deployment.

### Step 6 — Bootstrap CDK and synthesize

Both cdk bootstrap and cdk synth/cdk deploy automatically read your CDK context (from ~/.cdk.json or the project's cdk.json) — you do not pass the values as flags. (You can still override or add individual values with -c KEY=VALUE, which take precedence over the file.)

> **Important:** You must run npx cdk bootstrap before npx cdk synth / npx cdk deploy in each account and Region. Bootstrap creates the CDK toolkit resources (staging S3 bucket, ECR repo, IAM roles) that synth/deploy rely on. It is a one-time setup per account and Region.

First, make sure your AWS CLI is pointed at the target account and Region, then bootstrap (one-time per account and Region). Bootstrap provisions the CDK toolkit stack; it does not need the RES parameters, but running it from the repo is expected:

```
export AWS_REGION=<region>

npx cdk bootstrap aws://<account-id>/<region>
```

> **Tip:** Set your Region explicitly (via export AWS_REGION=<region>, your profile, or --region) and pass aws://<account-id>/<region> to bootstrap/deploy. If the Region is left unset, CDK falls back to whatever is in your local AWS config — and if a stack with the same name already exists in that other Region, CDK will update that one instead of creating yours. Passing the explicit account/region avoids this.

Then synthesize. This is where your CDK context values are consumed (each RES parameter is read via try_get_context and json.loads), so a successful synth confirms your context is well-formed and picked up:

```
npx cdk synth
```

To inspect the exact context values CDK resolved (from ~/.cdk.json, cdk.json, cdk.context.json, and any -c flags combined):

```
npx cdk context
```

If a RES value is missing or wrong, fix it in your context file (~/.cdk.json or cdk.json — check the "context" wrapper and JSON-escaped values) and re-run npx cdk synth.

### Step 7 — Push your source to CodeCommit

Get the repository clone URL from the AWS console: open the [CodeCommit console](https://console.aws.amazon.com/codesuite/codecommit/repositories) in your target Region, select the DigitalEngineeringPlatform repository, and choose Clone URL → copy the HTTPS (or SSH) URL. Make sure you have set up CodeCommit access for that method — see [Setting up for AWS CodeCommit](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up.html).

#### Push

Add the CodeCommit URL as a git remote, commit any changes you want to test, and push your working
branch:

```
git remote add <remote-name> <clone-url>
git add <changed-files>
git commit -m "<description>"
git push <remote-name> develop
```

The pipelines you deploy next watch the develop branch of this repository, so push to develop.

> **Note:** CodeCommit supports three connection methods — pick the one that matches how you authenticate (details in the [setup guide](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up.html)):

> HTTPS with Git credentials — simplest; a static username/password generated in IAM. Use the HTTPS clone URL.

> SSH — an SSH key pair associated with your IAM user. Use the SSH clone URL.

> git-remote-codecommit (GRC) — if you use IAM Identity Center (SSO), federated, or temporary credentials. Install with pip install git-remote-codecommit, then use the URL form codecommit::<region>://DigitalEngineeringPlatform.

### Step 8 — Deploy the build pipeline

> **Note:** What this pipeline does. RESBuildPipelineStack creates the main [AWS CodePipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/welcome.html) that builds RES from your source (web portal, container images, packaging), runs the security-audit / unit-test / coverage stages, and — when deploy=true — deploys the RES environment stack (Deploy-ResearchAndEngineeringStudio) and optionally runs integration tests. It is the source-to-environment loop; every push to the watched branch re-runs it.

Deploy RESBuildPipelineStack. Which command you run depends on the external-resources path you chose in Prerequisites / Step 5.

#### Option A — Bring-your-own external resources (recommended)

```
npx cdk deploy RESBuildPipelineStack \
  -c repository_name=DigitalEngineeringPlatform \
  -c branch_name=develop \
  -c deploy=true \
  -c integration_tests=false
```

> Custom domain (optional): If you configured custom domain names in your CDK context (`CustomDomainNameforWebApp`, `CustomDomainNameforVDI`) and have a Route 53 hosted zone for your domain, add `-c portal_domain_name=<your-domain>` to the deploy command. This adds a pipeline step that automatically creates updates the DNS records pointing to the RES load balancers. Without it, you need to create the DNS records manually after deployment.

#### Option B — Batteries Included (RES provisions the external resources)

> **Editor's note.** "Batteries Included" and "RES-provisioned external resources" are the same thing
> in this guide. The `batteries_included` context flag, the `BatteriesIncluded` stack and
> `BIStackTemplateURL` are the literal identifiers in the source.

Add batteries_included=true and the BIStackTemplateURL (the public external-resources CloudFormation template that creates the VPC/AD/EFS). The pipeline's Deploy stage then deploys the BatteriesIncluded stack first, then the RES environment stack (the dependency is enforced automatically):

```
npx cdk deploy RESBuildPipelineStack \
  -c repository_name=DigitalEngineeringPlatform \
  -c branch_name=develop \
  -c deploy=true \
  -c integration_tests=false \
  -c batteries_included=true \
  -c BIStackTemplateURL=https://s3.amazonaws.com/aws-hpc-recipes/main/recipes/res/res_demo_env/assets/bi.yaml
```

> The CLI will pause and prompt for confirmation before applying any IAM or security-group changes. Review the listed changes, then approve to deploy.

#### Deploy-command flag reference

All flags are passed as CDK context (-c KEY=VALUE). Booleans are parsed case-insensitively as value.lower() == "true", so pass the literal string true/false. Source of truth: PipelineStack in source/idea/pipeline/stack.py and source/idea/app.py.

| Flag | Default | What it does |
| --- | --- | --- |
| repository_name | DigitalEngineeringPlatform | CodeCommit repo the pipeline's Source stage pulls from. |
| branch_name | develop | Branch the pipeline watches; a push to it triggers an execution. |
| deploy | false | When true, adds the Deploy stage that deploys the RES environment stack (Deploy-ResearchAndEngineeringStudio). When false, the pipeline builds/scans/tests but does not deploy RES. |
| integration_tests | true | When true, runs post-deploy integration tests (component/infra-host, AD-sync, API, smoke). When false, skips them. Only has effect when deploy=true. If omitted it defaults to running, so you must explicitly pass integration_tests=false to skip. |
| batteries_included | false | When true, the Deploy stage first deploys the BatteriesIncluded stack (VPC/AD/EFS) and switches parameter resolution to BIParameters (SSM-backed). Requires BIStackTemplateURL. See Step 5 Option B. |
| BIStackTemplateURL | "" | URL of the RESExternal CFN template BI deploys. Required when batteries_included=true. |
| use_bi_parameters_from_ssm | false | Use BIParameters sourced from existing SSM parameters (BI already ran previously). When true, the Deploy stage does not re-create the BI stack. |
| destroy | false | Adds a teardown step that destroys the deployed environment after the other post-deploy steps complete. |
| destroy_batteries_included | false | Also tear down the BI stack. |
| portal_domain_name | "" | If set, adds the create-web-and-VDI DNS-record step and orders integ tests after it. |
| ecr_public_repository_name | "" | Override the public ECR repo (publish path only); defaults to the built-in public RES repo. |
| publish_templates | false | Publishes artifacts to the public research-engineering-studio-<region> buckets (which your account does not own, so it fails with AccessDenied). Leave it false. |
| test_suite | dev | (2026.09+) Which integration-test suite runs post-deploy: dev (fast, per-commit), nightly, or release. Only applies when integration_tests=true. See Running the nightly test suite. |
| testing_infra_included | false | (2026.09+) When true, also deploys a testing-infrastructure stack that provisions extra storage (EFS + FSx for Lustre + FSx for ONTAP) used by the nightly/release suites. Requires the Amazon\*TemplateURL context keys. Not needed for a normal dev deploy. |
| ontap_ad_join | false | (2026.09+) When true, joins the test FSx for ONTAP storage to the Active Directory (needs AD details via ADDnsIPs, and the AD controller security group to allow VPC traffic). Only relevant with testing_infra_included=true. |
| source_trigger | events | Controls the CodeCommit commit trigger. "events" (default) fires the pipeline on every push; "none" disables the commit trigger -user this with `schedule_trigger=true` for a schedule-only pipeline. |
| schedule_trigger | false | When true, adds an EventBrige rule that starts the pipeline on the `schedule_cron` schedule. Used by scheduled pipelines. |
| schedule_cron | cron(0 9 ? * MON-FRI* \*) | UTC cron exprression for the scheduled trigger. Default is 9:00 UTC on weekdays. Only applies when `scheduled_trigger=true` |
| use_rhel9_infra_ami | false | (2026.09+) When true, overrides the infrastructure host AMI with RHEL9 from the base software stack config. |

> **Note:** test_suite, testing_infra_included, and ontap_ad_join are available in RES 2026.09 and later and are only needed to run the heavier nightly / release test suites — not for a normal dev deploy. See Running the nightly test suite.

#### Running the nightly test suite

> **Note:** Advanced / optional (RES 2026.09+). This is only for running the heavier nightly (or release) integration-test suite, which needs extra test storage (EFS + FSx for Lustre + FSx for ONTAP). Skip this for a normal dev deploy.

To run the nightly suite, add the storage-template URLs and ADDnsIPs to your ~/.cdk.json, then deploy with the extra flags. ADDnsIPs takes a different form depending on how your external resources are provisioned:

Case 1 — Bring-your-own external resources (you supply literal values). Add:

```
"AmazonEFSTemplateURL": "https://s3.amazonaws.com/aws-hpc-recipes/main/recipes/storage/efs_simple/assets/main.yaml",
"AmazonFSxForLustreTemplateURL": "https://s3.amazonaws.com/aws-hpc-recipes/main/recipes/storage/fsx_lustre/assets/scratch.yaml",
"AmazonFSxForONTAPTemplateURL": "https://s3.amazonaws.com/aws-hpc-recipes/main/recipes/storage/fsx_ontap/assets/main.yaml",
"ADDnsIPs": "\"<AD domain-controller IPs, comma-separated, e.g. 10.3.144.170,10.3.130.121>\""
```

Case 2 — Batteries Included (you deploy the BI stack in your pipeline, or use use_bi_parameters_from_ssm=true). Use the SSM path form for ADDnsIPs (replace <env-name>):

```
"AmazonEFSTemplateURL": "https://s3.amazonaws.com/aws-hpc-recipes/main/recipes/storage/efs_simple/assets/main.yaml",
"AmazonFSxForLustreTemplateURL": "https://s3.amazonaws.com/aws-hpc-recipes/main/recipes/storage/fsx_lustre/assets/scratch.yaml",
"AmazonFSxForONTAPTemplateURL": "https://s3.amazonaws.com/aws-hpc-recipes/main/recipes/storage/fsx_ontap/assets/main.yaml",
"ADDnsIPs": "\"/<env-name>/external/ADDnsIPs\""
```

> **Note:** In Case 2, that SSM parameter must exist. Either re-deploy the BI stack through the pipeline (which creates it), or manually create an SSM parameter named /<env-name>/external/ADDnsIPs of type String whose value is the AD domain-controller IPs, comma-separated (e.g. 10.3.144.170,10.3.130.121).

Then update your pipeline, appending the two flags:

```
npx cdk deploy RESBuildPipelineStack \
  -c repository_name=DigitalEngineeringPlatform \
  -c branch_name=develop \
  -c deploy=true \
  -c integration_tests=true \
  -c test_suite=nightly \
  -c testing_infra_included=true \
  -c ontap_ad_join=true
```

(Add -c batteries_included=true -c BIStackTemplateURL=<url> for Case 2 if you are deploying the BI stack here.)

### Step 9 — Deploy the host modules pipeline

> **Note:** What this pipeline does. RESHostModulesPipelineStack creates a separate CodePipeline that builds and publishes the host modules — the compiled software artifacts installed on RES hosts (cluster-manager, VDC, VDI, bastion-host, DCV broker/gateway, etc.) — to an S3 bucket. For personal development you publish to a bucket you own (public_release=false) rather than the public RES distribution buckets. RES hosts download these modules on boot, so this pipeline is what gets your host-side code changes onto the instances.

> **Editor's note.** This guide gives `public_release` both values for this step: the note above says
> `public_release=false` for personal development, the command below sets `true`, and the flag table
> says `s3_bucket_name` is "Required when `public_release=false`". The operative fact is that a
> deployed cluster's bootstrap reads host modules from the `latest/` path, which only the
> `public_release=true` wave populates. Confirm against
> `source/infra/host_modules_pipeline/stack.py` before relying on either value.

Deploy RESHostModulesPipelineStack. For personal development, publish the host modules to your own S3 bucket by setting public_release=true and providing s3_bucket_name:

```
npx cdk deploy RESHostModulesPipelineStack \
  -c repository_name=DigitalEngineeringPlatform \
  -c branch_name=develop \
  -c publish_modules=true \
  -c public_release=true\
  -c s3_bucket_name=res-staging-<region>-<account-id>
```

Context flags:

- publish_modules=true — build and publish the host modules.
- public_release=true — add the publish-to-`latest` waves (with a manual-approval gate). Required so modules reach the `latest` folder the bootstrap reads.
- s3_bucket_name — the bucket the host modules are published to.

##### Deploy-command flag reference

All flags are passed as CDK context (-c KEY=VALUE). Booleans are parsed case-insensitively as value.lower() == "true", so pass the literal string true/false. Source of truth: HostModulePipelineStack in source/infra/host_modules_pipeline/stack.py.

| Flag | Default | What it does |
| --- | --- | --- |
| repository_name | DigitalEngineeringPlatform | CodeCommit repo the pipeline's Source stage pulls from. |
| branch_name | develop | Branch the pipeline watches; a push to it triggers an execution. |
| publish_modules | false | When true, adds the Publish wave that uploads the built host modules to S3. When false, the pipeline builds and unit-tests the modules but does not publish them. public_release and s3_bucket_name are only read when this is true. |
| public_release | false | Adds the publish-to-latest wave (manual-approval + publish). The bootstrap reads from latest, so set true to have your modules picked up; false publishes only to the versioned folder. |
| s3_bucket_name | "" | The bucket host modules are published to. Required when public_release=false. Reuse the res-staging-<region>-<account-id> bucket that RESBuildPipelineStack created. |

> **Note:** The host modules pipeline builds both x86_64 and arm64, and publish.sh refuses to overwrite an existing version (host_modules/<module>/<version>/<arch>/...). To republish a changed module, bump its version in source/infra/host_modules/modules.json first.

> Deploy RESBuildPipelineStack before RESHostModulesPipelineStack.

### Step 10 — Run the pipeline

Deploying the stacks in Steps 8–9 creates the CodePipelines and triggers a first execution automatically — you do not need to start it manually.

Watch it in the [CodePipeline console](https://console.aws.amazon.com/codesuite/codepipeline/pipelines): select the pipeline whose name starts with RESBuildPipelineStack and follow the stages: Source → Build → UpdatePipeline → Assets → SecurityAudit → UnitTests → Deploy. A full run takes roughly 75 minutes, and ~45 minutes longer if you used Batteries Included (Option B), since the pipeline also provisions the VPC/AD/EFS (the BatteriesIncluded stack) before deploying RES. The lint/type check and the ViperLight scan are not part of the shipped pipeline, and because you deployed with -c integration_tests=false (Step 8) the run also skips the post-deploy integration tests.

> **Note:** On a brand-new deployment the first execution can fail because freshly created IAM roles have not finished propagating when the pipeline starts. This is expected — re-run it from the CodePipeline console with Release change (or Retry on the failed stage).

Host modules pipeline. The RESHostModulesPipelineStack runs as its own CodePipeline; watch it the same way. With the dev setup (public_release=false, your own s3_bucket_name — Step 9) it builds and publishes to your bucket with no approval gate.

### Step 11 — Verify the deployment

The deployment is successful when all three of these hold. The console is the easiest way to check each:

1. The pipeline stages all succeed. In the [CodePipeline console](https://console.aws.amazon.com/codesuite/codepipeline/pipelines), confirm every stage of your build pipeline shows Succeeded.
2. The RES environment stack reaches CREATE_COMPLETE (or UPDATE_COMPLETE). In the [CloudFormation console](https://console.aws.amazon.com/cloudformation/) (target Region), find the stack named Deploy-ResearchAndEngineeringStudio and confirm its status.
3. The RES web portal is reachable. In the CloudFormation console, open the Deploy-ResearchAndEngineeringStudio stack's Outputs tab, find the web portal URL, and open it in a browser (your source IP must be within the client_ip CIDR you configured). On first deployment RES creates the clusteradmin Cognito user and emails a temporary password to your AdministratorEmail. (Note: This password might have been reset to the password specified in ~/.cdk.json depending if tests where ran) (Step 5) — log in as clusteradmin with that password (you'll set a new one on first login) to confirm the portal loads. Check spam if it doesn't arrive. If you used an existing/external Cognito pool where clusteradmin already exists, RES sends no email — use that pool's credentials instead.

---

## Publishing templates and host modules to your own buckets (self-hosted distribution)

> **Advanced / optional.** This is a variant of the flow above. Use it when you want the pipeline to **generate the RES CloudFormation install template and all of its deployment artifacts into S3 buckets and an ECR repository that you own**, so that template can be handed to others and deployed into **any account and any Region** — without depending on the public `research-engineering-studio-*` distribution buckets that the RES team owns. Typical case: a Cloud Support / field engineer generates a template and hands it to a customer who deploys it in their own account.

> **Warning:** This produces **publicly readable** S3 buckets and a **public** ECR repository — required for the cross-account distribution model below. Confirm your account's security posture allows public artifact buckets before proceeding.

It reuses Steps 1–7 above (clone, Python env, build libraries, CodeCommit repo, CDK context, push). It **replaces** Steps 8–9 with publish-mode variants, and adds source edits and bucket setup.

### How it works and the one decision you must make first

When `publish_templates=true`, `source/idea/app.py` swaps in a `BootstraplessStackSynthesizer` and bakes the artifact location into the generated template as:

```
s3://<ARTIFACTS_BUCKET_PREFIX_NAME>-${AWS::Region}/releases/<version>/...
```

`${AWS::Region}` resolves **at deploy time to the Region the template is deployed into**. So:

- **The template JSON is Region-agnostic** — one file deploys into any Region you support.
- **The artifacts are not.** Every Region needs its own bucket `<prefix>-<region>` **in that Region**, populated with the artifacts. A Lambda function's S3 code bucket must be in the same Region as the function, so you cannot serve all Regions from one central bucket.

**The decision:** S3 bucket names are globally unique, so `<prefix>-<region>` can exist in exactly **one** account. Pick a single **hosting account** that owns the public buckets + public ECR repo and runs the publish pipelines. Every consumer — in any account, in any Region you have populated — deploys the same template reading from that hosting account's public buckets. Do **not** try to have multiple accounts self-host under the same prefix.

**What a deployment of the generated template consumes:**

| Artifact | Location | Produced by |
| --- | --- | --- |
| Install template JSON | `s3://<prefix>-<region>/releases/<ver>/ResearchAndEngineeringStudio.template.json` | Build pipeline — Publish wave |
| CDK asset zips (Lambda + layers) | `s3://<prefix>-<region>/releases/<ver>/<hash>` | Build pipeline — Publish wave (`cdk-assets publish`) |
| Bootstrap tarballs (`*.tar.gz`) | `s3://<prefix>-<region>/releases/<ver>/` | Build pipeline — Publish wave |
| Host modules (`*.so`) | `s3://<prefix>-<region>/host_modules/<name>/latest/<arch>/<name>.so` | Host modules pipeline — Publish + PublishToLatest waves |
| AD-Sync container image | your **public** ECR repo (global, one repo for all Regions) | Build pipeline — Publish wave |

At deploy time the RES install stack pulls the AD-Sync image from your public ECR into the consuming account's *own private* ECR; RES hosts then read the tarballs and host modules from `<prefix>-<region>` on boot.

### Additional prerequisites

1. **A hosting account** you administer, where the publish pipelines run and the public buckets/ECR live.
2. **A prefix** — a globally-unique S3 name stem, e.g. `acme-res`. Buckets will be `acme-res-<region>`.
3. **The list of Regions** you support. Keep it small — one bucket per Region, and every listed Region is published to on each run.
4. **A public ECR repository** you own (ECR Public is a single global registry; one repo covers all Regions). Note its name.

### Step P1 — Repoint the artifact prefix and Region lists in source

The destination is driven by the constant `ARTIFACTS_BUCKET_PREFIX_NAME`, **defined in three files** (only the first is imported by the deploy/publish/bootstrap paths today; the other two are duplicates kept for drift safety) plus **one hardcoded literal** in a bootstrap script. Set every one to your prefix:

| File / line | What it is | Required? |
| --- | --- | --- |
| `source/idea/constants.py:7` | The constant actually consumed (app, pipelines, bucket helper) | **Yes** |
| `source/idea/infrastructure/install/constants.py:39` | Duplicate definition (currently unused) | Recommended (drift safety) |
| `source/idea/idea-data-model/src/ideadatamodel/constants.py:611` | Duplicate definition (currently unused) | Recommended (drift safety) |
| `source/idea/idea-bootstrap/resources/scripts/common/linux/host_modules.sh` — the `research-engineering-studio-${AWS_REGION}` fallback | Priority-3 fallback the host-module bootstrap uses if the DynamoDB lookup fails | **Yes** — otherwise a lookup failure silently falls back to the RES public bucket |

Also trim the onboarded-Region lists to the Regions you support — there are **two independent copies**:

- `source/idea/pipeline/stack.py` — `ONBOARDED_REGIONS` / `ONBOARDED_REGIONS_GOVCLOUD`
- `source/infra/host_modules_pipeline/stack.py` — its own `ONBOARDED_REGIONS` / `ONBOARDED_REGIONS_GOVCLOUD`

Both publish loops iterate their list, and every listed Region must have a pre-created bucket.

> **Note:** If you pass `-c ecr_public_repository_name=<yours>` on the deploy command (Step P3), you don't have to edit code for ECR. Only change the `PUBLICECRRepository` fallback default in `source/idea/pipeline/stack.py` if you want to guarantee the RES public repo is never referenced when the flag is omitted.

Commit these edits on `develop` and push to CodeCommit (Step 7) so the pipelines build from them.

### Step P2 — Create the public artifact buckets

Create one bucket `<prefix>-<region>` **in each supported Region**, publicly readable, with S3-managed encryption. The publish scripts only `cp`/`put-object`/`rm` — they never create buckets.

Helper: `source/idea/pipeline/scripts/helpers/create_s3_release_buckets.sh` reads the prefix from `idea.constants`, creates `<prefix>-<region>` across enabled Regions with versioning, and attaches the publish CodeBuild role policy. It does **not** make them public — layer that on:

- A bucket policy granting `s3:GetObject` to `Principal: *`, scoped to `releases/*` and `host_modules/*`.
- **Account-level and bucket-level Block Public Access must permit that policy** or the grant is silently ignored → `AccessDenied` at deploy.
- **SSE-S3 (AES256)**, not a KMS CMK — a CMK would force cross-account `kms:Decrypt` grants on every consuming account.

> **Note:** The consuming account's CloudFormation fetches asset zips, and RES instances `s3 cp` the tarballs/modules using their instance role — the public bucket policy satisfies the resource side, and instance-role identity permissions are unchanged, so no template-side IAM edits are needed.

### Step P3 — Deploy the build pipeline in publish mode

Deploy `RESBuildPipelineStack` with `publish_templates=true` and your public ECR repo. This adds a **Publish** wave (upload template + assets + tarballs to every `<prefix>-<region>`, and push the AD-Sync image to your public ECR), a **manual-approval** gate (`ManualApprovalForLatestBucketRefresh`), and a **`/latest` refresh** wave.

```
npx cdk deploy RESBuildPipelineStack \
  -c repository_name=DigitalEngineeringPlatform \
  -c branch_name=develop \
  -c deploy=true \
  -c integration_tests=true \
  -c publish_templates=true \
  -c ecr_public_repository_name=<your-public-ecr-repo>
```

> **Note:** The Publish wave writes the versioned release into every `<prefix>-<region>` bucket, then the pipeline **pauses at `ManualApprovalForLatestBucketRefresh`**. Approving it runs the `/latest` refresh, which copies `releases/<version>/` into `releases/latest/` in each bucket. Approve only once the versioned artifacts look correct.

### Step P4 — Deploy the host modules pipeline in fan-out mode

Unlike Step 9 (which sets `s3_bucket_name` to publish to a single personal staging bucket), for self-hosted distribution **omit `s3_bucket_name`** so the pipeline fans out to `res-staging-<region>-<account>` **and every `<prefix>-<region>` regional bucket**:

```
npx cdk deploy RESHostModulesPipelineStack \
  -c repository_name=DigitalEngineeringPlatform \
  -c branch_name=develop \
  -c publish_modules=true \
  -c public_release=true
```

- `public_release=true` — **required**: the deployed cluster's bootstrap reads host modules from `.../latest/...`. Without it, only the versioned path is populated and host-module download fails on boot.
- **No `s3_bucket_name`** — triggers the regional fan-out (Source: `publish.sh` / `publish_latest.sh` under `source/infra/host_modules_pipeline/scripts/`).

> **Important:** Deploy `RESBuildPipelineStack` (Step P3) before `RESHostModulesPipelineStack`, and run this pipeline in the **same hosting account** so `host_modules/` lands in the same `<prefix>-<region>` buckets the install template reads from.

### Step P5 — Verify: deploy the generated template from a clean account

The only check that proves the whole distribution is to deploy the published template **from a separate account** into each supported Region:

- Download the generated template.
- Launch the generated template following the [public documentation](https://docs.aws.amazon.com/res/latest/ug/launch-the-product.html) instead of using the template provided in the documentation.

A successful create in a fresh account simultaneously confirms: cross-account read of the public bucket (asset zips + tarballs); correct per-Region artifact placement; **no CDK bootstrap dependency** (the bootstrapless template does not require the consuming account to have run `cdk bootstrap`); AD-Sync image pulls from your public ECR; and host modules download on host boot from `<prefix>-<region>/host_modules/.../latest/...`. If a clean account can deploy in Region *X*, every consumer can.

### Self-hosted gotchas

- **Per-Region, not global.** Instances read their own Region's bucket and Lambda code must be co-located, so you need a bucket per supported Region. Supporting only one Region reduces this to a single bucket.
- **Two `/latest` gates.** Both pipelines hold a `/latest` promotion behind manual approval (`ManualApprovalForLatestBucketRefresh` and `ApprovePublishingToLatest`). The deployed template and bootstrap both consume `/latest`, so neither is complete until you approve.
- **ECR is global.** One public ECR repo covers all Regions.
- **Encryption / BPA.** SSE-S3 only; ensure account + bucket Block Public Access allow the public read policy.
- **Deploy-side IAM is unchanged.** Permissions a consuming account needs to create RES resources are inherent to RES and unaffected by where artifacts are hosted; the buckets only need to be readable.

---

## Developer workflow

Once the environment is deployed, you can iterate on RES source in two ways.

### Option 1 — Push to CodeCommit (full pipeline re-run)

The standard loop: commit your change and push to the branch the pipeline watches (develop). The push automatically triggers the build pipeline, which rebuilds, re-deploys the RES environment stack, and (if enabled) re-runs tests.

```
git add <changed-files>
git commit -m "<description>"
git push <remote-name> develop
```

- Use it for: any change, and always before you consider a change "done" — it is the source of truth and exercises the real build/deploy path.
- Trade-off: slowest loop (full build + deploy).

### Option 2 — Local patch (fast, targeted iteration)

For a quick edit-test cycle you can patch a running environment directly, without a full pipeline run, using the RES patch tools (RES ≥ 2025.12). You build just the changed component locally and push it to the environment. Pick the target by what you changed:

> **Note:** Some local build steps here require [Docker](https://docs.docker.com/get-docker/) (for example, building the RES library Lambda layer in Option C). Docker is not needed to deploy via the pipeline — only for these local builds.

A. Infra host / VDI module (cluster-manager, virtual-desktop-controller, virtual-desktop, bastion-host, dcv-gateway, or installation):

```
# Build the module (produces dist/idea-<module>-<version>.tar.gz)
invoke clean.<module> build.<module> package.<module>

# Push it to the running environment
python3 res_tool.py \
  --environment-name <env-name> \
  --module <module> \
  --zip-file dist/idea-<module>-<version>.tar.gz \
  --s3-bucket <res-staging-bucket> \
  --partition <Classic|GovCloud>
```

The tool uploads the package to s3://<bucket>/patches/, repoints the module's \*.app_package_uri key in the <env-name>.cluster-settings DynamoDB table (saving the previous value for rollback), and grants the module's IAM role read access to the object. Then:

- Infra hosts (cluster-manager, VDC, bastion, dcv-gateway): terminate the module's EC2 instance — the Auto Scaling group relaunches one that pulls the patched package on boot.
- virtual-desktop: launch a new VDI session to pick up the update.

B. Backend Lambda and RES API:

The RES API is defined with Smithy models (which generate the OpenAPI specs) under source/res/api/. See source/res/api/README.md for the API structure and how to add or change operations before building and deploying your changes with the workflow below.

```
cd source/idea/backend
  zip -r backend-lambda-$(git rev-parse --short=8 HEAD).zip . -x "*.pyc" -x
  "__pycache__/*"
cd -

python3 res_lambda_tool.py \
  --zip-file backend-lambda-<commit-hash>.zip \
  --lambda-name <env-name>-backend-lambda \
  --s3-bucket <res-staging-bucket>
```

The tool saves the current function code to s3://<bucket>/res-patch-state/... for rollback, then calls update_function_code. The zip filename must end in unique hash (eg. commit hash) `-<commit-hash>.zip` — the tool derives the rollback key from it.

> Recommend using `git rev-parse --short=8 HEAD` for generating the unique hash.

Note: The same approach patches any other RES Lambda — no compile step, just zip the target function's own source folder (instead of source/idea/backend) and pass it plus the deployed function's name (--lambda-name) to res_lambda_tool.py. Function code lives under:

- source/idea/infrastructure/resources/lambda_functions/
- source/idea/infrastructure/resources/lambda_functions/custom_resource/
- source/idea/infrastructure/resources/lambda_functions_with_utils/
- source/idea/infrastructure/install/handlers/

Use the deployed function name, not the folder name for `--lambda-name` , the actual deployed function name could be found in the AWS Lambda console.

C. RES library (shared code → Lambda layer):

```
# 1. Build the layer zip. generate_lambda_layer.py builds the library + data-model,
#    Docker-builds the layer bundle, and outputs lambda-layer-<commit-hash>.zip
#    (the filename MUST end in -<commit-hash>.zip; Docker required).
python3 generate_lambda_layer.py --project-root . --version <version>

# 2. Publish the layer and repoint every function in the environment that uses it:
python3 res_lambda_layer_tool.py \
  --environment-name <env-name> \
  --stack-name <root-cfn-stack-name> \
  --zip-file lambda-layer-<commit-hash>.zip \
  --lambda-layer <layer-name> \
  --s3-bucket <res-staging-bucket> \
  --partition <Classic|GovCloud>
```

generate_lambda_layer.py runs invoke build/package for the library and data-model, then builds the layer via the RES library-layer Dockerfile. The patch tool then publishes a new layer version and finds every Lambda in the environment stacks that references the layer, repointing it at the new version (saving the previous mapping to S3).

> **Note:** Local patching is a fast iteration shortcut against a live environment, not a substitute for the pipeline. It mutates the deployed environment out-of-band, so once your change is right, land it through Option 1 (push to CodeCommit) so the pipeline and source remain the source of truth. If a fix touches shared code (idea-sdk, library, data-model) you may need to patch multiple modules and/or the Lambda layer.

### Patch script source

The scripts referenced above. Save each into the project root (the version suffix, e.g. 2026.06, tracks your RES version) and run with python3. The patch tools require the AWS CLI/Boto3 configured for the account and Region where RES is deployed; generate_lambda_layer.py also requires Docker.

generate_lambda_layer.py — build the RES library Lambda layer zip

```
import argparse
import os
import shutil
import subprocess

parser = argparse.ArgumentParser(description="Generate RES library lambda layer locally")
parser.add_argument("--project-root", help="Path to the project root directory", required=True, type=str)
parser.add_argument("--version", help="RES version", required=True, type=str)
args = parser.parse_args()

if not os.path.exists(args.project_root):
    print(f"Path to project root directory {args.project_root} doesn't exist")
    exit(1)

# Commit hash — the patch tool derives the rollback key from the -<hash>.zip suffix
commit_hash = subprocess.check_output(
    ["git", "rev-parse", "--short=8", "HEAD"],
    cwd=args.project_root,
    text=True,
).strip()

# Build the library and data-model
print(f"Building library and data-model in {args.project_root}")
subprocess.check_call(
    [
        "invoke",
        "clean.library", "build.library", "package.library",
        "clean.datamodel", "build.datamodel", "package.datamodel",
    ],
    cwd=args.project_root,
)

work_dir = os.getcwd()
print(f"Working in {work_dir}")

# Locate the build outputs
library_path = os.path.join(args.project_root, "dist", f"library-{args.version}")
library_tar_file = os.path.join(library_path, "library-lib.tar.gz")
requirements_file = os.path.join(library_path, "requirements.txt")
data_model_path = os.path.join(args.project_root, "dist", f"datamodel-{args.version}")
data_model_tar_file = os.path.join(data_model_path, "datamodel-lib.tar.gz")

for path in (library_tar_file, requirements_file, data_model_tar_file):
    if not os.path.exists(path):
        print(f"Required file {path} doesn't exist")
        exit(1)

# Copy the build inputs into the Docker build context
shutil.copy(library_tar_file, "library-lib.tar.gz")
shutil.copy(requirements_file, "requirements.txt")
shutil.copy(data_model_tar_file, "datamodel-lib.tar.gz")

# Build the layer image using the RES library-layer Dockerfile
dockerfile_path = os.path.join(
    args.project_root, "source/idea/infrastructure/install/library_lambda_layer/Dockerfile"
)
subprocess.check_call([
    "docker", "build",
    "--build-arg", "LIBRARY_TAR_FILE=library-lib.tar.gz",
    "--build-arg", "LIBRARY_REQUIREMENTS_FILE=requirements.txt",
    "--build-arg", "DATA_MODEL_TAR_FILE=datamodel-lib.tar.gz",
    "-f", dockerfile_path,
    "-t", "lambda-layer-builder",
    ".",
])

# Extract the built layer content from the image
subprocess.check_call(["docker", "create", "--name", "temp-container", "lambda-layer-builder"])
subprocess.check_call(["docker", "cp", "temp-container:/asset/.", "./layer-content/"])
subprocess.check_call(["docker", "rm", "temp-container"])

# Zip the layer with the commit-hash suffix the patch tool expects
layer_zip_name = f"lambda-layer-{commit_hash}.zip"
os.chdir("layer-content")
subprocess.check_call(["zip", "-r", f"../{layer_zip_name}", "."])
os.chdir("..")

# Clean up
os.remove("library-lib.tar.gz")
os.remove("requirements.txt")
os.remove("datamodel-lib.tar.gz")
shutil.rmtree("layer-content")

print(f"Layer zip created: {os.path.join(work_dir, layer_zip_name)}")
```

res_tool.py — infra host / VDI module patch

```
import argparse
import boto3
import os
import json

parser = argparse.ArgumentParser(description="Update RES module package URI")
parser.add_argument(
    "--environment-name", help="Name of the RES environment", required=True, type=str
)
parser.add_argument(
    "--module",
    help="Name of the module to update",
    required=True,
    type=str,
    choices=["cluster-manager", "virtual-desktop-controller", "virtual-desktop", "installation", "bastion-host", "dcv-gateway"],
)
parser.add_argument("--zip-file", help="Path to the zip file", required=True, type=str)
parser.add_argument("--s3-bucket", help="S3 bucket name", required=True, type=str)
parser.add_argument(
    "--partition",
    help="AWS partition",
    required=False,
    type=str,
    choices=["Classic", "GovCloud"],
    default="Classic",
)
parser.add_argument(
    "--rollback",
    help="Rollback to original package URI",
    action="store_true",
    default=False,
)

args = parser.parse_args()

# Map module names to DDB keys
if args.module == "virtual-desktop-controller":
    module_key = "vdc.controller"
elif args.module == "virtual-desktop":
    module_key = "vdi-app"
elif args.module == "dcv-gateway":
    module_key = "vdc.dcv_connection_gateway"
else:
    module_key = args.module

ddb_key = "cluster.installation_scripts_uri" if args.module == "installation" else f"{module_key}.app_package_uri"
backup_ddb_key = f"{ddb_key}.pre_patch_backup"

session = boto3.session.Session()
s3_client = session.client("s3")
dynamodb_client = session.client("dynamodb")
iam_client = session.client("iam")

if args.rollback:
    # Restore original DDB value from backup key
    response = dynamodb_client.get_item(
        TableName=f"{args.environment_name}.cluster-settings",
        Key={"key": {"S": backup_ddb_key}},
    )
    item = response.get("Item")
    if not item:
        print(f"ERROR: No backup found at DDB key '{backup_ddb_key}'. Cannot rollback.")
        exit(1)

    original_uri = item["value"]["S"]
    print(f"Rolling back {ddb_key} to original value: {original_uri}")
    dynamodb_client.update_item(
        TableName=f"{args.environment_name}.cluster-settings",
        Key={"key": {"S": ddb_key}},
        UpdateExpression="SET #val = :val",
        ExpressionAttributeNames={"#val": "value"},
        ExpressionAttributeValues={":val": {"S": original_uri}},
    )
    dynamodb_client.delete_item(
        TableName=f"{args.environment_name}.cluster-settings",
        Key={"key": {"S": backup_ddb_key}},
    )
    print(f"Successfully restored {ddb_key} to {original_uri}")
    print("Please terminate the existing infra instance and wait for a new one to be launched automatically.")
    exit(0)

# 1. Save current DDB value for rollback
response = dynamodb_client.get_item(
    TableName=f"{args.environment_name}.cluster-settings",
    Key={"key": {"S": ddb_key}},
)
item = response.get("Item")
if item:
    original_uri = item.get("value", {}).get("S")
    print(f"Original {ddb_key} value: {original_uri}")
    try:
        dynamodb_client.put_item(
            TableName=f"{args.environment_name}.cluster-settings",
            Item={"key": {"S": backup_ddb_key}, "value": {"S": original_uri}},
            ConditionExpression="attribute_not_exists(#k)",
            ExpressionAttributeNames={"#k": "key"},
        )
    except dynamodb_client.exceptions.ConditionalCheckFailedException:
        print(f"Backup already exists at {backup_ddb_key}; preserving the original value.")

# 2. Upload zip file to S3
zip_filename = os.path.basename(args.zip_file)
s3_key = f"patches/{zip_filename}"
s3_uri = f"s3://{args.s3_bucket}/{s3_key}"

print(f"Uploading {args.zip_file} to {s3_uri}")
s3_client.upload_file(args.zip_file, args.s3_bucket, s3_key)
print(f"Successfully uploaded to {s3_uri}")
s3_client.put_object_tagging(
    Bucket=args.s3_bucket,
    Key=s3_key,
    Tagging={"TagSet": [{"Key": "res:EnvironmentName", "Value": args.environment_name}]},
)

# 3. Update DynamoDB record
print(f"Updating {ddb_key} to {s3_uri}")
dynamodb_client.update_item(
    TableName=f"{args.environment_name}.cluster-settings",
    Key={"key": {"S": ddb_key}},
    UpdateExpression="SET #val = :val",
    ExpressionAttributeNames={"#val": "value"},
    ExpressionAttributeValues={":val": {"S": s3_uri}}
)
print(f"Successfully updated {ddb_key} to {s3_uri}")

# 4. Update IAM role with S3 GetObject permission
MODULE_ROLE_MAP = {
    "cluster-manager": "cluster-manager-role",
    "virtual-desktop-controller": "vdc-controller-role",
    "virtual-desktop": "vdc-host-scoped-down-role",
    "bastion-host": "bastion-host-role",
    "dcv-gateway": "vdc-gateway-role",
}

if args.module == "installation":
    role_names = [f"{args.environment_name}-{r}" for r in MODULE_ROLE_MAP.values()]
else:
    role_names = [f"{args.environment_name}-{MODULE_ROLE_MAP[args.module]}"]

policy_name = f"{args.environment_name}-s3-patch-access"
aws_partition = "aws-us-gov" if args.partition == "GovCloud" else "aws"
s3_resource_arn = f"arn:{aws_partition}:s3:::{args.s3_bucket}/{s3_key}"

for role_name in role_names:
    # Get existing policy if it exists
    try:
        existing_policy = iam_client.get_role_policy(
            RoleName=role_name,
            PolicyName=policy_name
        )
        policy_document = existing_policy['PolicyDocument']

        # Add new resource to existing statement
        resources = policy_document['Statement'][0].get('Resource', [])
        if isinstance(resources, str):
            resources = [resources]
        if s3_resource_arn not in resources:
            resources.append(s3_resource_arn)
        policy_document['Statement'][0]['Resource'] = resources

    except iam_client.exceptions.NoSuchEntityException:
        # Policy doesn't exist, create new one
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "s3:GetObject",
                    "Resource": [s3_resource_arn]
                }
            ]
        }

    print(f"Updating IAM role {role_name} with S3 access to {s3_resource_arn}")
    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document)
    )

if args.module == "virtual-desktop":
    print("Please launch a new VDI to use the updated package.")
elif args.module == "installation":
    print("Patch applied successfully for installation scripts.")
else:
    print("Please terminate the existing infra instance and wait for a new one to be launched automatically.")
```

res_lambda_tool.py — backend Lambda function patch

```
import argparse
import boto3
import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.request import urlopen

STATE_KEY_PREFIX = "res-patch-state/lambda-code"

def extract_commit_hash(zip_file_path):
    """Extract commit hash from zip filename (e.g. backend-lambda-abc12345.zip -> abc12345)."""
    basename = os.path.basename(zip_file_path)
    # Match the last segment before .zip as the commit hash
    match = re.match(r'.+-([a-f0-9]+)\.zip$', basename)
    if not match:
        print(f"ERROR: Cannot extract commit hash from zip filename: {basename}")
        print("Expected format: <prefix>-<commit-hash>.zip (e.g. backend-lambda-abc12345.zip)")
        sys.exit(1)
    return match.group(1)

def get_state_key(lambda_name, commit_hash):
    """Generate S3 key for rollback state."""
    safe_name = lambda_name.replace("/", "_").replace(":", "_")
    return f"{STATE_KEY_PREFIX}/{safe_name}/{commit_hash}/state.json"

def get_backup_key(lambda_name, commit_hash):
    """Generate S3 key for backup zip."""
    safe_name = lambda_name.replace("/", "_").replace(":", "_")
    return f"{STATE_KEY_PREFIX}/{safe_name}/{commit_hash}/backup.zip"

def patch(lambda_client, s3_client, bucket, lambda_name, zip_file):
    """Apply patch: save current state to S3, then update function code."""
    commit_hash = extract_commit_hash(zip_file)
    print(f"Commit hash: {commit_hash}")

    # Get current function code location for rollback
    print(f"Saving current state for rollback...")
    current_config = lambda_client.get_function(FunctionName=lambda_name)
    code_location = current_config['Code']['Location']

    # Download current deployment package
    print(f"Downloading current deployment package...")
    response = urlopen(code_location)
    current_zip_content = response.read()

    # Upload backup zip to S3 (guard against overwriting on retry)
    backup_key = get_backup_key(lambda_name, commit_hash)
    state_key = get_state_key(lambda_name, commit_hash)

    try:
        s3_client.head_object(Bucket=bucket, Key=state_key)
        print(f"Backup state already exists at s3://{bucket}/{state_key}, skipping backup to preserve original code.")
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] != '404':
            raise
        # No existing state; safe to create the backup
        print(f"Uploading backup to s3://{bucket}/{backup_key}")
        s3_client.put_object(
            Bucket=bucket,
            Key=backup_key,
            Body=current_zip_content
        )

        # Upload state metadata to S3
        state = {
            "lambda_name": lambda_name,
            "commit_hash": commit_hash,
            "backup_key": backup_key,
            "patched_at": datetime.now(timezone.utc).isoformat(),
            "original_code_sha256": current_config['Configuration'].get('CodeSha256', ''),
        }
        s3_client.put_object(
            Bucket=bucket,
            Key=state_key,
            Body=json.dumps(state, indent=2)
        )
        print(f"Rollback state saved to s3://{bucket}/{state_key}")

    # Apply the patch
    print(f"Updating Lambda function: {lambda_name}")
    with open(zip_file, 'rb') as f:
        zip_content = f.read()

    lambda_client.update_function_code(
        FunctionName=lambda_name,
        ZipFile=zip_content
    )
    print(f"Patch applied successfully to {lambda_name}")

def rollback(lambda_client, s3_client, bucket, lambda_name, zip_file):
    """Rollback a specific patch identified by the commit hash in the zip filename."""
    commit_hash = extract_commit_hash(zip_file)
    state_key = get_state_key(lambda_name, commit_hash)

    # Load state from S3
    print(f"Looking for rollback state for commit: {commit_hash}")
    try:
        response = s3_client.get_object(Bucket=bucket, Key=state_key)
        state = json.loads(response['Body'].read())
    except s3_client.exceptions.NoSuchKey:
        print(f"ERROR: No rollback state found for commit {commit_hash}")
        print(f"  Looked at: s3://{bucket}/{state_key}")
        print("Either this commit was never patched, or it was already rolled back.")
        sys.exit(1)

    # Download backup zip from S3
    backup_key = state['backup_key']
    print(f"Rolling back commit {commit_hash} (patched at {state['patched_at']})...")
    print(f"Downloading backup from s3://{bucket}/{backup_key}")

    response = s3_client.get_object(Bucket=bucket, Key=backup_key)
    zip_content = response['Body'].read()

    # Restore the function code
    lambda_client.update_function_code(
        FunctionName=lambda_name,
        ZipFile=zip_content
    )

    # Clean up S3 state
    s3_client.delete_object(Bucket=bucket, Key=state_key)
    s3_client.delete_object(Bucket=bucket, Key=backup_key)
    print(f"Rollback of commit {commit_hash} completed successfully. S3 state cleaned up.")

def main():
    parser = argparse.ArgumentParser(description="Patch Lambda function with new code (supports rollback via S3)")
    parser.add_argument("--zip-file", help="Path to the Lambda code zip file", required=True, type=str)
    parser.add_argument("--lambda-name", help="Lambda function name", required=True, type=str)
    parser.add_argument("--s3-bucket", help="S3 bucket for storing rollback state", required=True, type=str)
    parser.add_argument("--rollback", help="Rollback the patch identified by the zip file's commit hash", action="store_true")

    args = parser.parse_args()

    session = boto3.session.Session()
    lambda_client = session.client('lambda')
    s3_client = session.client('s3')

    if args.rollback:
        rollback(lambda_client, s3_client, args.s3_bucket, args.lambda_name, args.zip_file)
    else:
        patch(lambda_client, s3_client, args.s3_bucket, args.lambda_name, args.zip_file)

if __name__ == "__main__":
    main()
```

res_lambda_layer_tool.py — RES library (Lambda layer) patch

> **Editor's note.** The source for this script is not included in this guide, although the Developer
> workflow section above instructs you to run it. The other three patch tools are listed in full. Obtain
> it from the RES team, or use the pipeline path (Option 1) instead of the local-patch path for changes
> that touch the RES library.

## Cleanup

To avoid ongoing charges, delete everything you created when you are done. The simplest way is the CloudFormation console ([console.aws.amazon.com/cloudformation](https://console.aws.amazon.com/cloudformation/), in your target Region) — delete the stacks in this order:

- Deploy-ResearchAndEngineeringStudio — the RES environment stack. Select it and choose Delete. Wait for it to reach DELETE_COMPLETE before continuing.

> **Important:** After this stack deletes, manually delete the shared-storage security group (in the EC2 console → Security Groups, look for <environment-name>-shared-storage-security-group). RES stack deletions always leave it behind — which also blocks VPC/prerequisite-stack cleanup later. If a network interface (ENI) still uses it, detach/delete those ENIs first, then delete the security group manually.

- RESHostModulesPipelineStack — the host modules pipeline stack.
- RESBuildPipelineStack — the build pipeline stack.

Then clean up the resources you created manually for this walkthrough:

- CodeCommit repository — in the [CodeCommit console](https://console.aws.amazon.com/codesuite/codecommit/repositories), select DigitalEngineeringPlatform → Settings → Delete repository.
- res-staging-\* S3 bucket — empty it, then delete it in the S3 console.
- Any network/directory prerequisite stacks you created only for testing (e.g. the external resources stack).

> **Note:** If a stack deletion fails, open the stack's Events tab in the CloudFormation console to see which resource blocked it (commonly an S3 bucket or ECR repository that still has contents). Empty that resource, then delete the stack again.

## Troubleshooting

- npx cdk bootstrap fails: S3 asset bucket already exists. An orphaned CDK staging bucket exists without a matching CDKToolkit stack. Delete the stuck CDKToolkit stack, empty and remove cdk-hnb659fds-assets-<account-id>-<region> (including all object versions and delete markers — versioning is on), then bootstrap again.
- The build (synth) stage fails on isort / black / lint checks. The lint line in source/idea/pipeline/scripts/synth/commands.sh is commented out, so this happens only if you enable it. tox -e lint,type then runs first and can flag files as "incorrectly sorted/formatted"; the script stops before CDK runs, surfacing a downstream no matching base directory path found for cdk.out error. Fix forward: run isort source and black . (pinned versions from requirements/lint.txt), commit, and push. It takes effect only after you push to the pipeline's branch.
- CDK deploys to the wrong Region. Set the Region explicitly (export AWS_REGION=<region>) and pass aws://<account-id>/<region> to bootstrap/deploy; otherwise CDK falls back to the Region in your local AWS config.
- The pipeline has no source / fails immediately at the source stage. Confirm you pushed your branch to CodeCommit (Step 7) and that repository_name / branch_name match what you pushed.
- The first execution failed right after deploying the stacks. Expected on a fresh deploy (IAM role propagation timing). Re-run from the CodePipeline console with Release change (or Retry on the failed stage).
- The Deploy stage fails with Certificate ARN '""' is not valid. You are deploying with Batteries Included (batteries_included=true) without a custom domain. Batteries Included generates the web-portal certificate from PortalDomainName — set PortalDomainName (and CustomDomainNameforWebApp / CustomDomainNameforVDI) to a public domain you own (Step 5, Option B), then re-run the pipeline.
- RESHostModulesPipelineStack modules publish to s3_bucket_name., which must exist. RESBuildPipelineStack creates res-staging-<region>-<account-id> — deploy it first and reuse that name or create your own bucket with aws s3 mb.
- Cannot reach the web portal. Confirm your public IP is within the ClientIp CIDR you set in your CDK context (~/.cdk.json), and that the load balancer is internet-facing (is_load_balancer_internet_facing=true) if connecting from the internet.

## Related documentation

- [RES User Guide](https://docs.aws.amazon.com/res/latest/ug/)
- [RES Installation (released version)](https://docs.aws.amazon.com/res/latest/ug/deploy-the-product.html)
- [RES Troubleshooting wiki](https://github.com/aws/res/wiki/Troubleshooting)
- [Contributing to RES](https://github.com/aws/res/blob/mainline/CONTRIBUTING.md)