#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

S3_BUCKET_ARN_PREFIX_REGEX = "^arn:aws(?:-cn|-us-gov)?:s3:::[^/]+/(.*)"
S3_BUCKET_ARN_REGEX = "^(?:arn:(?:aws(?:-cn|-us-gov)?)):s3:::([a-z0-9][a-z0-9-.]{1,61}[a-z0-9])(?:/[a-z0-9-.]+)*/?$"

OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX = "PROJECT_NAME_PREFIX"
OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX = "PROJECT_NAME_AND_USERNAME_PREFIX"
OBJECT_STORAGE_NO_CUSTOM_PREFIX = "NO_CUSTOM_PREFIX"

FSTAB_PATH = "/etc/fstab"
MODPROBE_CONFIG_PATH = "/etc/modprobe.d/modprobe.conf"

SYSTEMD_SERVICE_FILE_DIR = "/etc/systemd/system"
