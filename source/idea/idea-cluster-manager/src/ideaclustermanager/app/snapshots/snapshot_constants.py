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

SNAPSHOT_S3_BUCKET_NAME_REGEX = r'^[a-z0-9]+[\.\-\w]*[a-z0-9]+$'
SNAPSHOT_PATH_REGEX = r'^([\w\.\-\!\*\'\(\)]+[\/]*)+$'

METADATA_FILE_NAME_AND_EXTENSION = "metadata.json"
TABLE_EXPORT_DESCRIPTION_KEY = "table_export_descriptions"
VERSION_KEY = "version"
