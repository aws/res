#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

pip install --upgrade pip
pip uninstall -y pyOpenSSL
pip install -r requirements/dev.txt
pip install source/idea/idea-data-model/src
pip install ".[dev]"
