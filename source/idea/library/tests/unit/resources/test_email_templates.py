#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


import unittest
from typing import Dict, Optional

import pytest
import res.exceptions as exceptions
from res.resources import email_templates
from res.utils import table_utils

TEST_TEMPLATE_NAME = "template name"
TEST_TEMPLATE_TYPE = "template type"
TEST_TEMPLATE_NAME_2 = "template name 2"
TEST_TEMPLATE_TYPE_2 = "template type 2"
INVALID_TEMPLATE_NAME = "invalid template name"


class EmailTemplatesTestContext:
    email_templates: Optional[Dict]


class TestEmailTemplates(unittest.TestCase):

    def setUp(self):
        self.context: EmailTemplatesTestContext = EmailTemplatesTestContext()
        self.context.email_template = {
            email_templates.EMAIL_TEMPLATE_DB_NAME_KEY: TEST_TEMPLATE_NAME,
            email_templates.EMAIL_TEMPLATE_DB_TEMPLATE_TYPE_KEY: TEST_TEMPLATE_TYPE,
            "builtin": True,
        }
        table_utils.create_item(
            email_templates.EMAIL_TEMPLATE_TABLE_NAME, item=self.context.email_template
        )

    def test_email_template_get_invalid_template_should_fail(self):
        """
        get email template failure
        """
        with pytest.raises(exceptions.EmailTemplateNotFound) as exc_info:
            email_templates.get_email_template(INVALID_TEMPLATE_NAME)
        assert (
            f"Email template with name: {INVALID_TEMPLATE_NAME} not found"
            in exc_info.value.args[0]
        )

    def test_email_template_get_valid_template_should_pass(self):
        """
        get email template success
        """
        result = email_templates.get_email_template(TEST_TEMPLATE_NAME)
        assert result is not None
        assert (
            result.get(email_templates.EMAIL_TEMPLATE_DB_NAME_KEY) == TEST_TEMPLATE_NAME
        )
        assert (
            result.get(email_templates.EMAIL_TEMPLATE_DB_TEMPLATE_TYPE_KEY)
            == TEST_TEMPLATE_TYPE
        )
        assert result.get("builtin") == True

    def test_email_template_create_template_should_pass(self):
        """
        create email template success
        """
        created_email_template = email_templates.create_email_template(
            email_template={
                email_templates.EMAIL_TEMPLATE_DB_NAME_KEY: TEST_TEMPLATE_NAME_2,
                email_templates.EMAIL_TEMPLATE_DB_TEMPLATE_TYPE_KEY: TEST_TEMPLATE_TYPE_2,
                "builtin": False,
            }
        )

        assert (
            created_email_template[email_templates.EMAIL_TEMPLATE_DB_NAME_KEY]
            is not None
        )
        assert (
            created_email_template[email_templates.EMAIL_TEMPLATE_DB_TEMPLATE_TYPE_KEY]
            is not None
        )
        assert created_email_template["builtin"] is False

        email_template_from_db = email_templates.get_email_template(
            TEST_TEMPLATE_NAME_2
        )

        assert email_template_from_db is not None
        assert (
            email_template_from_db[email_templates.EMAIL_TEMPLATE_DB_NAME_KEY]
            == created_email_template[email_templates.EMAIL_TEMPLATE_DB_NAME_KEY]
        )
        assert (
            email_template_from_db[email_templates.EMAIL_TEMPLATE_DB_TEMPLATE_TYPE_KEY]
            == created_email_template[
                email_templates.EMAIL_TEMPLATE_DB_TEMPLATE_TYPE_KEY
            ]
        )
        assert email_template_from_db["builtin"] == created_email_template["builtin"]

    def test_email_template_create_template_with_duplicate_name_should_fail(self):
        """
        create email template failure
        """
        with pytest.raises(Exception) as exc_info:
            email_templates.create_email_template(
                email_template={
                    email_templates.EMAIL_TEMPLATE_DB_NAME_KEY: TEST_TEMPLATE_NAME,
                    email_templates.EMAIL_TEMPLATE_DB_TEMPLATE_TYPE_KEY: TEST_TEMPLATE_TYPE_2,
                    "builtin": False,
                }
            )
        assert (
            f"Email template with name: {TEST_TEMPLATE_NAME} already exists"
            in exc_info.value.args[0]
        )

    def test_email_template_create_template_without_name_should_fail(self):
        """
        create email template failure
        """
        with pytest.raises(Exception) as exc_info:
            email_templates.create_email_template(
                email_template={
                    email_templates.EMAIL_TEMPLATE_DB_TEMPLATE_TYPE_KEY: TEST_TEMPLATE_TYPE_2,
                    "builtin": False,
                }
            )
        assert "template.name is required" in exc_info.value.args[0]

    def test_email_template_create_template_without_type_should_fail(self):
        """
        create email template failure
        """
        with pytest.raises(Exception) as exc_info:
            email_templates.create_email_template(
                email_template={
                    email_templates.EMAIL_TEMPLATE_DB_NAME_KEY: TEST_TEMPLATE_NAME_2,
                    "builtin": False,
                }
            )
        assert "template.template_type is required" in exc_info.value.args[0]

    def test_email_template_list_templates_should_pass(self):
        """
        list email template success
        """
        email_templates_list = email_templates.list_email_templates()
        email_templates_names = [
            template[email_templates.EMAIL_TEMPLATE_DB_NAME_KEY]
            for template in email_templates_list
        ]
        assert len(email_templates_names) == 2
        assert TEST_TEMPLATE_NAME in email_templates_names
        assert TEST_TEMPLATE_NAME_2 in email_templates_names
