# Support

## Dates

2026.09 is the final release of Research and Engineering Studio.

Support ends on **2027-09-30**. That is the End of Support Life of the 2026.09 release, which follows the
published AWS support policy: End of Support Life falls on the last day of the release month in the
following year.

Until that date, RES remains supported.

## What support covers

The support policy covers RES itself and RES-specific integration behavior.

Amazon DCV, which powers the virtual desktops, is a separately supported AWS product with its own
lifecycle, so a DCV problem has its own support path after RES support ends.

The AWS services RES runs on have their own lifecycles as well, including EC2, EFS, FSx, Cognito, AWS
Managed Microsoft AD, Application Load Balancer, and Secrets Manager.

## Where to raise an issue

Through your existing AWS Support agreement, as you do now.

For a security vulnerability, follow [`SECURITY.md`](./SECURITY.md) instead. Do not open a public issue.

## After support ends

What ends is AWS's support obligation. A RES deployment runs in your own account, under your own
control, and keeps running. Individual dependencies do age: pinned AMIs reach their vendor deprecation
dates, certificates expire on their own schedule, and third-party packages fetched at launch change
independently of RES. `docs/reference/external-dependencies.md` covers what to watch.

Three paths are open to you.

### Continue on RES

Either support it yourself or engage a third party to support it for you.

#### Supporting it yourself

RES is open source under the Apache License 2.0. `docs/develop/deploying-from-source.md` covers
building and deploying from source, `docs/operate/diagnosing-failures.md` covers diagnosis, and
`docs/reference/external-dependencies.md` lists every artifact outside the repository that a deployment
depends on. No patch or release procedure is published; a fork defines its own.

Keeping RES current becomes your work: maintaining the pinned AMI tables, tracking the third-party
dependencies fetched at install and boot time, and triaging security findings against your own
deployment.

#### Engaging a third party

Systems integrators and consulting firms can take on RES capability and maintain or extend it for you.
Your AWS account team can discuss options with you.

#### Maintaining a fork

If you need changes and want to own them, fork the repository. See [`FORKS.md`](./FORKS.md).

### Move to an AWS managed service

Amazon WorkSpaces and Amazon WorkSpaces Applications provide managed virtual desktops, and AWS Parallel
Computing Service provides DCV-enabled login nodes for HPC access. None is a drop-in replacement for the
RES portal, so plan for some change to how your users work.

### Move to an alternative product

Other portals deliver virtual desktops on AWS, both commercial and open source. If you go this way, the
data and configuration in your deployment are yours: user identities live in your directory, files live
on your filesystems, and neither is locked to RES.

## The repository itself

This repository's contents stay available to read, clone, and fork. If you need a copy whose
availability you control, keep your own clone. See [`MAINTAINERS.md`](./MAINTAINERS.md) and
[`FORKS.md`](./FORKS.md).
