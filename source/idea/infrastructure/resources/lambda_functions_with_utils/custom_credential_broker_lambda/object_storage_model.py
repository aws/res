#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List, Optional

OBJECT_STORAGE_DB_PROJECTS_KEY = "projects"
OBJECT_STORAGE_DB_READ_ONLY_KEY = "read_only"


class ObjectStorageModel:
    def __init__(
        self,
        filesystem_name: str,
        projects: List[str],
        read_only: bool,
        bucket_arn: str,
        iam_role_arn: Optional[str] = None,
        custom_bucket_prefix: Optional[str] = None,
    ):
        self.filesystem_name = filesystem_name
        self.projects = projects
        self.read_only = read_only
        self.iam_role_arn = iam_role_arn
        self.custom_bucket_prefix = custom_bucket_prefix
        self.bucket_arn = bucket_arn

    def get_filesystem_name(self) -> str:
        return self.filesystem_name

    def get_projects(self) -> List[str]:
        return self.projects

    def is_read_only(self) -> bool:
        return self.read_only == True

    def get_iam_role_arn(self) -> Optional[str]:
        return self.iam_role_arn

    def get_custom_bucket_prefix(self) -> Optional[str]:
        return self.custom_bucket_prefix

    def get_bucket_arn(self) -> str:
        return self.bucket_arn
