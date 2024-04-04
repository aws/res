#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

pip install --upgrade pip
pip uninstall -y pyOpenSSL
pip install -r requirements/dev.txt
