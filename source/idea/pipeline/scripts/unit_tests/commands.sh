#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -ex

invoke clean.library build.library package.library
invoke clean.datamodel build.datamodel package.datamodel