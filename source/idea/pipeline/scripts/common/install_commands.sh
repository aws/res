#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

n 20.19.0
pyenv install 3.12.11
pyenv global 3.12.11
apt-get update
apt-get install -y libldap2-dev libsasl2-dev unzip
