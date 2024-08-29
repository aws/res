#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the 'License'). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

OBJECT_STORAGE_DB_PROJECTS_KEY = "projects"
OBJECT_STORAGE_DB_READ_ONLY_KEY = "read_only"


class ObjectStorageModel:
    def __init__(self, filesystem_name, projects, read_only, bucket_arn, iam_role_arn=None, custom_bucket_prefix=None):
        self.filesystem_name = filesystem_name
        self.projects = projects
        self.read_only = read_only
        self.iam_role_arn = iam_role_arn
        self.custom_bucket_prefix = custom_bucket_prefix
        self.bucket_arn = bucket_arn

    def get_filesystem_name(self):
        return self.filesystem_name

    def get_projects(self):
        return self.projects

    def is_read_only(self):
        return self.read_only == True

    def get_iam_role_arn(self):
        return self.iam_role_arn

    def get_custom_bucket_prefix(self):
        return self.custom_bucket_prefix

    def get_bucket_arn(self):
        return self.bucket_arn
