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

"""
Test Cases for SnapshotsService
"""

import json
from unittest.mock import MagicMock

import botocore.exceptions
import pytest
from ideaclustermanager import AppContext
from ideaclustermanager.app.snapshots.snapshots_service import DYNAMODB_TABLES_TO_EXPORT
from ideatestutils import IdeaTestProps

from ideadatamodel import (
    ListSnapshotsRequest,
    Snapshot,
    SnapshotStatus,
    errorcodes,
    exceptions,
)

test_props = IdeaTestProps()


def mock_export_response(**_):
    return {"ExportDescription": {}}


def mock_export_response_throws_exception(**_):
    raise botocore.exceptions.ClientError(
        operation_name="export_table_to_point_in_time",
        error_response={"Error": {"Message": "Internal Server Error"}},
    )


def mock_unsuccessful_list_response(**_):
    raise botocore.exceptions.ClientError(
        operation_name="get_object",
        error_response={"Error": {"Message": "Internal Server Error"}},
    )


def mock_get_object_response_invalid_metadata(**_):
    return {
        "table_export_descriptions": {
            "accounts.group-members": {"ExportStatus": "InvalidStatus"}
        }
    }


def mock_get_object_response_single_export_in_progress(**_):
    mock_metadata = {"table_export_descriptions": {}}
    for table_name in DYNAMODB_TABLES_TO_EXPORT:
        mock_metadata["table_export_descriptions"][table_name] = {
            "ExportStatus": SnapshotStatus.COMPLETED
        }
    mock_metadata["table_export_descriptions"]["accounts.users"] = {
        "ExportStatus": SnapshotStatus.IN_PROGRESS,
        "ExportArn": "MockArn",
    }
    return mock_metadata


def mock_describe_export_response_export_completed(**_):
    return {"ExportDescription": {"ExportStatus": SnapshotStatus.COMPLETED}}


def mock_describe_export_response_export_failed(**_):
    return {
        "ExportDescription": {
            "ExportStatus": SnapshotStatus.FAILED,
            "FailureMessage": "Some Failure Message",
        }
    }


def create_snapshot_for_list_snapshots_test(context: AppContext, monkeypatch):
    """
    Helper method to create a snapshot to perform tests for listing snapshots
    """
    monkeypatch.setattr(
        context.aws().dynamodb(), "update_continuous_backups", MagicMock()
    )
    monkeypatch.setattr(
        context.aws().dynamodb(), "export_table_to_point_in_time", mock_export_response
    )
    monkeypatch.setattr(context.aws().s3(), "put_object", MagicMock())
    s3_get_mock = MagicMock()
    body_mock = MagicMock()
    body_mock.read.return_value.decode.return_value = json.dumps(
        mock_get_object_response_single_export_in_progress(), default=str
    )
    s3_get_mock.side_effect = [{"Body": body_mock}]
    monkeypatch.setattr(context.aws().s3(), "get_object", s3_get_mock)
    context.snapshots.create_snapshot(
        snapshot=Snapshot(s3_bucket_name="some_bucket_name", snapshot_path="valid/path")
    )


def test_create_snapshot_with_missing_bucket_name_should_fail(context: AppContext):
    """
    create snapshot with missing bucket name should fail
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.snapshots.create_snapshot(snapshot=Snapshot(s3_bucket_name=""))
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "s3_bucket_name is required" in exc_info.value.message


def test_create_snapshot_with_invalid_bucket_name_should_fail(context: AppContext):
    """
    create snapshot with invalid bucket name that doesn't match the required regex pattern.
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.snapshots.create_snapshot(
            snapshot=Snapshot(s3_bucket_name="invalid@bucket_name")
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "s3_bucket_name must match regex" in exc_info.value.message


def test_create_snapshot_with_missing_snapshot_path_should_fail(context: AppContext):
    """
    create snapshot with missing snapshot path should fail
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.snapshots.create_snapshot(
            snapshot=Snapshot(s3_bucket_name="some_bucket_name", snapshot_path="")
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "snapshot_path is required" in exc_info.value.message


def test_create_snapshot_with_invalid_snapshot_path_should_fail(context: AppContext):
    """
    create snapshot with invalid snapshot path that doesn't match the required regex pattern.
    """
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.snapshots.create_snapshot(
            snapshot=Snapshot(
                s3_bucket_name="some_bucket_name", snapshot_path="invalid\\path"
            )
        )
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "snapshot_path must match regex" in exc_info.value.message


def test_create_snapshot_succeeds(context: AppContext, monkeypatch):
    """
    create snapshot with valid bucket name and snapshot path.
    """
    monkeypatch.setattr(
        context.aws().dynamodb(), "update_continuous_backups", MagicMock()
    )
    monkeypatch.setattr(
        context.aws().dynamodb(), "export_table_to_point_in_time", mock_export_response
    )
    monkeypatch.setattr(context.aws().s3(), "put_object", MagicMock())
    context.snapshots.create_snapshot(
        snapshot=Snapshot(s3_bucket_name="some_bucket_name", snapshot_path="valid/path")
    )

    expected_table_export_descriptions = {}
    for table_name in DYNAMODB_TABLES_TO_EXPORT:
        expected_table_export_descriptions[table_name] = {}

    expected_metadata = {
        "table_export_descriptions": expected_table_export_descriptions,
        "version": context.module_version(),
    }
    context.aws().s3().put_object.assert_called_with(
        Bucket="some_bucket_name",
        Key="valid/path/metadata.json",
        Body=json.dumps(expected_metadata, default=str),
    )


def test_create_snapshot_throws_exception_when_export_table_fails(
    context: AppContext, monkeypatch
):
    """
    create snapshot throws exception when exporting table fails
    """
    monkeypatch.setattr(
        context.aws().dynamodb(), "update_continuous_backups", MagicMock()
    )
    monkeypatch.setattr(
        context.aws().dynamodb(),
        "export_table_to_point_in_time",
        mock_export_response_throws_exception,
    )
    monkeypatch.setattr(context.aws().s3(), "put_object", MagicMock())
    with pytest.raises(botocore.exceptions.ClientError):
        context.snapshots.create_snapshot(
            snapshot=Snapshot(
                s3_bucket_name="some_bucket_name", snapshot_path="valid/path"
            )
        )
    context.aws().s3().put_object.assert_not_called()


def test_list_snapshots_throws_exception_when_fetching_snapshot_metadata(
    context: AppContext, monkeypatch
):
    """
    List snapshots throws exception when fetching snapshot metadata
    """
    monkeypatch.setattr(
        context.aws().dynamodb(), "update_continuous_backups", MagicMock()
    )
    monkeypatch.setattr(
        context.aws().dynamodb(), "export_table_to_point_in_time", mock_export_response
    )
    monkeypatch.setattr(context.aws().s3(), "put_object", MagicMock())
    monkeypatch.setattr(
        context.aws().s3(), "get_object", mock_unsuccessful_list_response
    )
    context.snapshots.create_snapshot(
        snapshot=Snapshot(s3_bucket_name="some_bucket_name", snapshot_path="valid/path")
    )
    result = context.snapshots.list_snapshots(ListSnapshotsRequest())
    assert result.listing is not None
    assert len(result.listing) == 1
    assert result.listing[0].status == SnapshotStatus.FAILED


def test_list_snapshots_updates_status_to_failed_for_invalid_metadata(
    context: AppContext, monkeypatch
):
    """
    List snapshots updates status to failed when invalid metadata is fetched.
    """
    monkeypatch.setattr(
        context.aws().dynamodb(), "update_continuous_backups", MagicMock()
    )
    monkeypatch.setattr(
        context.aws().dynamodb(), "export_table_to_point_in_time", mock_export_response
    )
    monkeypatch.setattr(context.aws().s3(), "put_object", MagicMock())
    s3_get_mock = MagicMock()
    body_mock = MagicMock()
    body_mock.read.return_value.decode.return_value = json.dumps(
        mock_get_object_response_invalid_metadata(), default=str
    )
    s3_get_mock.side_effect = [{"Body": body_mock}]
    monkeypatch.setattr(context.aws().s3(), "get_object", s3_get_mock)
    context.snapshots.create_snapshot(
        snapshot=Snapshot(s3_bucket_name="some_bucket_name", snapshot_path="valid/path")
    )
    result = context.snapshots.list_snapshots(ListSnapshotsRequest())
    assert result.listing is not None
    assert len(result.listing) == 1
    assert result.listing[0].status == SnapshotStatus.FAILED


def test_list_snapshots_updates_status_to_completed_failed_when_describe_export_fails(
    context: AppContext, monkeypatch
):
    """
    List snapshots updates status to failed when describe_export call throws exception
    """
    create_snapshot_for_list_snapshots_test(context, monkeypatch)
    monkeypatch.setattr(
        context.aws().dynamodb(),
        "describe_export",
        mock_describe_export_response_export_failed,
    )
    result = context.snapshots.list_snapshots(ListSnapshotsRequest())
    assert result.listing is not None
    assert len(result.listing) == 1
    assert result.listing[0].status == SnapshotStatus.FAILED


def test_list_snapshots_updates_status_to_completed_when_pending_export_completed(
    context: AppContext, monkeypatch
):
    """
    List snapshots updates status to completed when describe_export returns with a completed status
    """
    create_snapshot_for_list_snapshots_test(context, monkeypatch)
    monkeypatch.setattr(
        context.aws().dynamodb(),
        "describe_export",
        mock_describe_export_response_export_completed,
    )
    result = context.snapshots.list_snapshots(ListSnapshotsRequest())
    assert result.listing is not None
    assert len(result.listing) == 1
    assert result.listing[0].status == SnapshotStatus.COMPLETED
