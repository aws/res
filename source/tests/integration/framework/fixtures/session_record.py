#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import time
from typing import Any, Dict, List

import pytest
from res.resources import sessions  # type: ignore
from res.utils import table_utils  # type: ignore

from tests.integration.framework.fixtures.fixture_request import FixtureRequest

logger = logging.getLogger(__name__)


def create_session_record(
    table_name: str,
    session_id: str,
    owner: str,
    **additional_fields: Any,
) -> Dict[str, Any]:
    """
    Create a dummy session record in DynamoDB.

    Args:
        table_name: DynamoDB table name
        session_id: Session identifier
        owner: Session owner
        **additional_fields: Additional fields to include in the record

    Returns:
        The created session record
    """
    current_time_ms = int(time.time() * 1000)
    session_record = {
        "owner": owner,
        "idea_session_id": session_id,
        "name": f"test-session-{session_id}",
        "state": "READY",
        "created_on": current_time_ms,
        "updated_on": current_time_ms,
        "session_tags": [],
        "session_type": "CONSOLE",
        "software_stack": {},
        **additional_fields,
    }

    table_utils.create_item(table_name=table_name, item=session_record)
    logger.info(f"Created dummy session record: {session_id} for owner: {owner}")

    return session_record


def delete_session_record(table_name: str, session_id: str, owner: str) -> None:
    """
    Delete a dummy session record from DynamoDB.

    Args:
        table_name: DynamoDB table name
        session_id: Session identifier
        owner: Session owner
    """
    table_utils.delete_item(
        table_name=table_name,
        key={
            sessions.SESSION_DB_HASH_KEY: owner,
            sessions.SESSION_DB_RANGE_KEY: session_id,
        },
    )
    logger.info(f"Deleted session record: {session_id} for owner: {owner}")


@pytest.fixture
def session_record(
    request: FixtureRequest,
) -> List[Dict[str, Any]]:
    """
    Fixture for creating/deleting dummy session records in DynamoDB.

    Usage:
        @pytest.mark.parametrize("session_record", [
            [
                {"session_id": "test-123", "owner": "user1"},
                {"session_id": "test-456", "owner": "user2"},
            ]
        ], indirect=True)
        def test_something(session_record):
            # session_record is a list of created records
            pass

    If a param dict includes "project_fixture": True, the fixture will resolve
    the "project" fixture at runtime and set project.project_id on the session record.
    The test must also parametrize the "project" fixture when using this option.
    """
    params_list: List[Dict[str, Any]] = request.param
    records = []
    for p in params_list:
        session_id: str = p["session_id"]
        owner: str = p["owner"]
        additional_fields: Dict[str, Any] = {
            k: v
            for k, v in p.items()
            if k not in ["session_id", "owner", "project_fixture"]
        }
        if p.get("project_fixture"):
            project = request.getfixturevalue("project")
            additional_fields["project"] = {"project_id": project.project_id}
        record = create_session_record(
            table_name=sessions.SESSIONS_TABLE_NAME,
            session_id=session_id,
            owner=owner,
            **additional_fields,
        )
        records.append(record)

    def tear_down() -> None:
        for p in params_list:
            delete_session_record(
                sessions.SESSIONS_TABLE_NAME, p["session_id"], p["owner"]
            )

    request.addfinalizer(tear_down)

    return records
