#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

pip install --upgrade "pip>=23.0,<26.1" pip-tools==7.5.3
pip uninstall -y pyOpenSSL
pip install -r requirements/dev.txt
