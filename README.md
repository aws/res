# Digital Engineering Platform on AWS

## Table of content

- [Documentation](#public-documentation)
- [Installation](#public-installation)
- [Pre-requisites (MacOS)](#pre-requisites-macos)
	- [Homebrew](#homebrew)
	- [AWS CLI](#aws-cli-v2)
	- [Python](#python)
	- [NVM](#nvm-node-version-manager)
	- [AWS CDK](#aws-cdk-v2630)
	- [Yarn](#yarn)
	- [Docker](#docker-desktop-optional)
	- [Virtual Environment](#virtual-environment)
- [Developer Setup](#developer-setup)
	- [Install requirements](#install-requirements)
	- [Verify Setup](#verify-setup)
	- [Build & Package](#clean-build-and-package)
	- [Run admin script in developer mode](#run-idea-adminsh-in-developer-mode)
		- [Pro-tip for IDEs](#pro-developer-tip)
		- [Verify developer mode enabled](#verify-if-developer-mode-is-enabled)
		- [Additional Dev Configurations](#development-configurations)
	- [CI/CD for development](#cicd-for-development)
- [License](#license)

## Public Documentation

https://docs.ide-on-aws.com/

## Public Installation

You can skip this for developer environment setup.

Refer
to [IDEA Installation](https://docs.ide-on-aws.com/idea/first-time-users/install-idea)
for public installation instructions.

This solution collects anonymous operational metrics to help AWS improve the
quality of the solution.


## Pre-requisites (MacOS)

### Homebrew
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
```

### AWS CLI v2

```
brew install awscli
```

Refer [Configure AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)

### Python

Install pyenv to simplify managing multiple python versions on your system

```
brew install pyenv
```

Install Python v3.9.16

```
pyenv install --skip-existing 3.9.16
```

### NVM (Node Version Manager)

Install nvm to simplify managing multiple Node versions

```
brew install nvm
```

Install NodeJS v18.18.0

```
nvm install 18.18.0
nvm use 18.18.0

# to set default nodejs version to 18.18.0, run:
nvm alias default 18.18.0
```

### AWS CDK v2.63.0

_Note: Do NOT install CDK globally using npm -g or yarn global add_

Install CDK using instructions below:

```
mkdir -p ~/.idea/lib/idea-cdk && pushd ~/.idea/lib/idea-cdk
npm init --force --yes
npm install aws-cdk@2.63.0 --save
popd
```

**Upgrade Info**

If you want to upgrade CDK version for your existing IDEA dev environment, run:

```
invoke devtool.upgrade-cdk
```

### Yarn

```
brew install yarn
```

### Docker Desktop (Optional)

Follow instructions [here](https://docs.docker.com/desktop/mac/install/) to
install Docker Desktop
_Required if you are working with creating Docker Images_

### Virtual Environment

Create virtual environment

```
~/.pyenv/versions/3.9.16/bin/python3 -m venv venv
```

Activate the virtual environment

```
source venv/bin/activate
```

## Developer Setup

### Install Requirements

```
pip install -r requirements/dev.txt
```

***BigSur Note***: cryptography and orjson library requirements may fail to
install on macOS BigSur.

If the orjson package fails to install during the previous step, run:

```
brew install rust
# Upgrade your pip
python3 -m pip install --upgrade pip
```

To fix **cryptography**, follow the instructions mentioned here:
https://stackoverflow.com/questions/64919326/pip-error-installing-cryptography-on-big-sur

```
env LDFLAGS="-L$(brew --prefix openssl@1.1)/lib" CFLAGS="-I$(brew --prefix openssl@1.1)/include" pip install cryptography==41.0.4
```

### Verify Setup

Run below command to check if development environment is working as expected,
run:

```
invoke -l
```

Running this command should print output similar to the following:

```
$ invoke -l
Available tasks:

  admin.cdk-nag-scan                   perform cdk nag scan on all applicable cdk stacks
  admin.test-iam-policies              test and render all IAM policy documents
  apispec.all (apispec)                build OpenAPI 3.0 spec for all modules
  apispec.cluster-manager              cluster-manager api spec
  apispec.scheduler                    scheduler api spec
  apispec.virtual-desktop-controller   virtual desktop controller api spec
  build.administrator                  build administrator
  build.all (build)                    build all
  build.cluster-manager                build cluster manager
  build.data-model                     build data-model
  build.scheduler                      build scheduler
  build.sdk                            build sdk
  build.virtual-desktop-controller     build virtual desktop controller
  clean.administrator                  clean administrator
  clean.all (clean)                    clean all components
  clean.cluster-manager                clean cluster manager
  clean.data-model                     clean data-model
  clean.scheduler                      clean scheduler
  clean.sdk                            clean sdk
  clean.virtual-desktop-controller     clean virtual desktop controller
  cli.admin                            invoke administrator app cli
  cli.cluster-manager                  invoke cluster-manager cli
  cli.scheduler                        invoke virtual desktop controller cli
  devtool.build                        wrapper utility for invoke clean.<module> build.<module> package.<module>
  devtool.configure                    configure devtool
  devtool.ssh                          ssh into the workstation
  devtool.sync                         rsync local sources with remote development server
  devtool.update-cdk-version           update cdk version in all applicable places
  devtool.upgrade-cdk                  upgrade cdk version in $HOME/.idea/lib/idea-cdk to the latest supported version by IDEA
  devtool.upload-packages              upload packages
  docker.build                         build administrator docker image
  docker.prepare-artifacts             copy docker artifacts to deployment directory
  docker.print-commands                print docker push commands for ECR
  package.administrator                package administrator
  package.all (package)                package all components
  package.cluster-manager              package cluster manager
  package.make-all-archive             build an all archive containing all package archived
  package.scheduler                    package scheduler
  package.virtual-desktop-controller   package virtual desktop controller
  release.build-opensource-dist        build open source package for Github
  release.build-s3-dist                build s3 distribution package for global assets
  release.update-version               update idea release version in all applicable places
  req.install                          Install python requirements
  req.update                           Update python requirements using pip-compile.
  tests.administrator                  run administrator unit tests
  tests.all (tests)                    run unit tests for all components
  tests.cluster-manager                run cluster-manager unit tests
  tests.scheduler                      run scheduler unit tests
  tests.sdk                            run sdk unit tests
  tests.virtual-desktop-controller     run virtual desktop controller unit tests
  web-portal.serve                     serve web-portal frontend app in web-browser
  web-portal.typings                   convert idea python models to typescript
```

### Clean, Build and Package

```
invoke clean build package
```

### Run res-admin.sh in Developer Mode

The **RES_DEV_MODE** environment variable is used to indicate if res-admin.sh
or res-admin-windows.ps1 should use the Docker Image or Run from sources.

If RES_DEV_MODE=true, res-admin.sh will execute administrator app directly
using sources.
If RES_DEV_MODE=false (default), res-admin.sh will attempt to download the
docker image from the public ecr repo for the latest release version and execute
administrator app using Docker Container.
Export RES_DEV_MODE=true on your terminal, before executing res-admin.sh on
from project root.

Eg.

```
export RES_DEV_MODE=true
```

⚠️You will need to run **export RES_DEV_MODE=true**, each time you open a new
Terminal session.

⚠️ Adding RES_DEV_MODE to .zshrc or .bashrc is not recommended as you will not
be able to seamlessly switch between dev mode vs non-dev mode and test the
Docker Container based idea-administrator flow._

#### Pro Developer Tip

**IntelliJ IDEA or PyCharm Users**
If you are using IntelliJ IDEA or PyCharm, you can set default environment
variables for terminals in your IDE.

* Navigate to Preferences → Tools → Terminal
* Add `RES_DEV_MODE=true` and `LC_CTYPE=en_US.UTF-8` as environment variables.
  Any new terminal sessions from within the IDE will automatically include
  these.

**VS Code Users**

If you are using VS Code, you can create a Terminal Profile in your
settings.json file to have an easy way to spawn both Terminals.
An example:

* Open your settings.json file in VScode (Apple Key + ,)  - click one of the '
  Edit in settings.json' links
* Look for your platform terminal settings - In this example we add a new
  profile on OSX -
* VS Code - Terminal Settings for RES_DEV_MODE

```
"terminal.integrated.profiles.osx": {
    "RES_DEV_MODE": {
        "overrideName": true,
        "path": "/bin/bash",
        "args": [
            "-l"
        ],
        "env": {
            "RES_DEV_MODE": "true"
        }
    }
```

_Make sure to preserve the JSON syntax of your settings.json file, or you will
have problems!_

#### Verify if Developer Mode is enabled

To verify, if Developer Mode is enabled, run below command. This should print *
*(Developer Mode)** at the end of the banner.

```
./res-admin.sh about

'########::'########::'######::
 ##.... ##: ##.....::'##... ##:
 ##:::: ##: ##::::::: ##:::..::
 ########:: ######:::. ######::
 ##.. ##::: ##...:::::..... ##:
 ##::. ##:: ##:::::::'##::: ##:
 ##:::. ##: ########:. ######::
..:::::..::........:::......:::

 Research and Engineering Studio on AWS
          Version 3.0.0-beta.1
            (Developer Mode)
Suggested Development Settings
```

#### Development configurations

During the development phase it may be helpful to keep some of these settings in
mind

+ Suspend ASG actions when working on an ASG-managed instance and intent to
  patch/update or are working on something where the process may crash.
  This can reduce the re-warm time for an instance
+ Use the res-admin.sh `patch` functionality if applicable
+ Make sure to use the `debug` log profile settings
+ Enable payload tracing for API requests to get more details

```
./res-admin.sh config set Key=cluster.logging.audit_logs.enable_payload_tracing,Type=bool,Value=True --aws-region us-east-1 --cluster-name idea-eada
```

+ When changes have been made, rebuild packages using the following

```
invoke clean build package
```

+ Rebuilding the package can also take a target to speed up the process and only
  rebuild that specific page. For example - if working heavily on the
  cluster-manager, do the following

```
invoke clean.cluster-manager build.cluster-manager package.cluster-manager
```

_NOTE: Just be aware of any cross dependencies or changes to data-model and sdk.
If in doubt - clean/build/package them all. Better to make sure things are
rebuilt and not rebuild incorrectly._

### CI/CD for development

It is highly recommended to provision CI/CD pipeline in your AWS account during
the development phase of the solution. The pipeline allows any code change to be
tested through dependency scanning tools, unit tests, build and deployment of
DEP in your account.

#### Onboarding CI/CD pipeline in your account

+ CodeCommit: The pipeline
  uses [AWS CodeCommit](https://docs.aws.amazon.com/codecommit/latest/userguide/getting-started.html)
  as source. Create a codecommit repository in your account named
  `Digital-Engineering-Platform` The name of the repository should match
  with `repository_name` context variable in "DigitalEngineeringPlatform/cdk.json"
+ Git: Configure the created repository as remote for git pushes, so any commit
  pushed on the repository triggers the pipeline
+ CDK: The pipeline is defined as cdk app. Deploy the app using instructions
  highlighted here in "DigitalEngineeringPlatform/source/idea/pipeline/README.md"

***

## License

Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
