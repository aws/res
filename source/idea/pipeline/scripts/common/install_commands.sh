#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

n 18.18.0
apt-get update
apt-get install -y libldap2-dev libsasl2-dev
