#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any, Optional

from res.clients.aws import get_aws_provider  # type: ignore

from .object_storage_model import ObjectStorageModel

CLUSTER_SETTINGS_KEY = "key"
CLUSTER_SETTINGS_VALUE = "value"
CLUSTER_SETTINGS_TABLE_NAME = os.environ.get("CLUSTER_SETTINGS_TABLE_NAME", "")
SHARED_STORAGE_PREFIX = os.environ.get("SHARED_STORAGE_PREFIX", "")
STORAGE_PROVIDER_S3_BUCKET = os.environ.get("STORAGE_PROVIDER_S3_BUCKET", "")


class SharedStorageDB:
    def __init__(self, logger: logging.Logger):
        self.dynamodb = get_aws_provider().dynamodb_table()
        self.table = self.dynamodb.Table(CLUSTER_SETTINGS_TABLE_NAME)
        self.prefix = SHARED_STORAGE_PREFIX
        self.logger = logger

    def get_object_storage_projects(self, filesystem_name: str) -> Any:
        return self.get_shared_storage_db_item(
            key=self._get_object_storage_key(filesystem_name, "projects")
        )

    def is_provider_s3(self, filesystem_name: str) -> Any:
        return (
            self.get_shared_storage_db_item(
                key=self._get_object_storage_key(filesystem_name, "provider")
            )
            == STORAGE_PROVIDER_S3_BUCKET
        )

    def get_object_storage_read_only(self, filesystem_name: str) -> Any:
        return self.get_shared_storage_db_item(
            key=self._get_object_storage_key(filesystem_name, "read_only")
        )

    def get_object_storage_custom_bucket_prefix(self, filesystem_name: str) -> Any:
        return self.get_shared_storage_db_item(
            key=self._get_object_storage_key(filesystem_name, "custom_bucket_prefix")
        )

    def get_object_storage_iam_role_arn(self, filesystem_name: str) -> Any:
        return self.get_shared_storage_db_item(
            key=self._get_object_storage_key(filesystem_name, "iam_role_arn")
        )

    def get_object_storage_bucket_arn(self, filesystem_name: str) -> Any:
        return self.get_shared_storage_db_item(
            key=self._get_object_storage_key(filesystem_name, "bucket_arn")
        )

    def get_object_storage_model(
        self, filesystem_name: str
    ) -> Optional[ObjectStorageModel]:
        keys_needed = [
            "projects",
            "read_only",
            "custom_bucket_prefix",
            "iam_role_arn",
            "provider",
            "bucket_arn",
        ]
        keys = {
            self._get_object_storage_key(filesystem_name, key): key
            for key in keys_needed
        }

        try:
            response = self.dynamodb.batch_get_item(
                RequestItems={
                    CLUSTER_SETTINGS_TABLE_NAME: {
                        "Keys": [{CLUSTER_SETTINGS_KEY: key} for key in keys.keys()]
                    }
                }
            )
        except Exception as e:
            self.logger.error(f"Error during batch get item: {e}")
            return None

        object_storage = {}
        key_values = response.get("Responses", {}).get(CLUSTER_SETTINGS_TABLE_NAME, [])

        for item in key_values:
            storage_key = item.get(CLUSTER_SETTINGS_KEY)
            if storage_key in keys:
                object_storage[keys[storage_key]] = item.get(CLUSTER_SETTINGS_VALUE)

        # Check for required values
        required_values = ["projects", "read_only", "bucket_arn"]
        missing_values = [
            value for value in required_values if value not in object_storage
        ]
        if missing_values:
            raise ValueError(f"Missing required values: {missing_values}")
        if object_storage.get("provider") != STORAGE_PROVIDER_S3_BUCKET:
            raise ValueError(f"Object storage provider is not S3")

        # Construct and return the ObjectStorageModel instance
        if object_storage:
            return ObjectStorageModel(
                filesystem_name=filesystem_name,
                projects=object_storage.get("projects"),  # type: ignore
                read_only=object_storage.get("read_only"),  # type: ignore
                bucket_arn=object_storage.get("bucket_arn"),  # type: ignore
                iam_role_arn=object_storage.get("iam_role_arn"),
                custom_bucket_prefix=object_storage.get("custom_bucket_prefix"),
            )
        return None

    def get_shared_storage_db_item(self, key: str) -> Any:
        response = self.table.get_item(Key={CLUSTER_SETTINGS_KEY: key})
        if "Item" in response:
            return response["Item"][CLUSTER_SETTINGS_VALUE]
        return None

    def _get_object_storage_key(self, filesystem_name: str, key_type: str) -> str:
        if key_type == "projects":
            return f"{self.prefix}.{filesystem_name}.projects"
        elif key_type == "provider":
            return f"{self.prefix}.{filesystem_name}.provider"
        elif key_type == "read_only":
            return f"{self.prefix}.{filesystem_name}.{STORAGE_PROVIDER_S3_BUCKET}.read_only"
        elif key_type == "custom_bucket_prefix":
            return f"{self.prefix}.{filesystem_name}.{STORAGE_PROVIDER_S3_BUCKET}.custom_bucket_prefix"
        elif key_type == "iam_role_arn":
            return f"{self.prefix}.{filesystem_name}.{STORAGE_PROVIDER_S3_BUCKET}.iam_role_arn"
        elif key_type == "bucket_arn":
            return f"{self.prefix}.{filesystem_name}.{STORAGE_PROVIDER_S3_BUCKET}.bucket_arn"
        else:
            raise Exception(f"Unknown key type {key_type}")
