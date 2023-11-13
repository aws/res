#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

AWS_CLI_NOT_INSTALLED = """
# AWS Profile not found!

We could not find any AWS profiles to use for SOCA installation. Please ensure AWS cli is installed and configured.

To install AWS CLI, run:
```bash
$ pip3 install awscli
```

If AWS CLI is installed, please ensure it is configured to use an AWS Account. To configure aws cli, run:
```bash
$ aws configure
```

Refer to AWS CLI Docs (https://awscli.amazonaws.com/v2/documentation/api/latest/reference/index.html) for more information.

"""
