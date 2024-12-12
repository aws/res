#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import res.exceptions as exceptions
from res.utils import table_utils, time_utils

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

EMAIL_TEMPLATE_TABLE_NAME = "email-templates"
EMAIL_TEMPLATE_DB_NAME_KEY = "name"
EMAIL_TEMPLATE_DB_TEMPLATE_TYPE_KEY = "template_type"

BASE_DIR = Path(os.path.realpath(__file__)).parent.parent
BASE_PERMISSION_PROFILE_CONFIG_PATH = os.path.join(
    BASE_DIR, "templates", "base-permission-profile-config.yaml"
)


def create_email_template(email_template: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a email template
    validate required fields, add the email_template to DynamoDB.
    :return: the created email_template
    """

    template_name = email_template.get(EMAIL_TEMPLATE_DB_NAME_KEY, "")
    template_type = email_template.get(EMAIL_TEMPLATE_DB_TEMPLATE_TYPE_KEY, "")
    if not email_template:
        raise Exception(f"email_template is required")
    if not template_name:
        raise Exception(f"template.name is required")
    if not template_type:
        raise Exception(f"template.template_type is required")

    try:
        if get_email_template(template_name):
            raise Exception(
                f"Email template with name: {email_template[EMAIL_TEMPLATE_DB_NAME_KEY]} already exists"
            )
    except exceptions.EmailTemplateNotFound:
        pass

    logger.info(
        f"Creating email template with name {email_template[EMAIL_TEMPLATE_DB_NAME_KEY]}"
    )
    current_time_ms = time_utils.current_time_ms()
    email_template["created_on"] = current_time_ms
    email_template["updated_on"] = current_time_ms
    created_email_template = table_utils.create_item(
        table_name=EMAIL_TEMPLATE_TABLE_NAME, item=email_template
    )
    logger.info(
        f"Successfully created email template with name {created_email_template[EMAIL_TEMPLATE_DB_NAME_KEY]}"
    )
    return created_email_template


def get_email_template(email_template_name: str) -> Dict[str, Any]:
    """
    Retrieve the EmailTemplate
    :param email_template_name
    :return: the EmailTemplate
    """

    if not email_template_name:
        raise Exception(f"template name is required")

    logger.info(f"Getting email template with name {email_template_name}")
    email_template = table_utils.get_item(
        table_name=EMAIL_TEMPLATE_TABLE_NAME,
        key={EMAIL_TEMPLATE_DB_NAME_KEY: email_template_name},
    )

    if not email_template:
        raise exceptions.EmailTemplateNotFound(
            f"Email template with name: {email_template_name} not found"
        )
    return email_template


def list_email_templates() -> List[Dict[str, Any]]:
    """
    List all EmailTemplates
    :return list of email templates
    """
    return table_utils.list_items(EMAIL_TEMPLATE_TABLE_NAME)


def is_email_templates_table_empty() -> bool:
    """
    Check if email template DDB is empty
    :return whether email template DDB is empty
    """
    return table_utils.is_table_empty(EMAIL_TEMPLATE_TABLE_NAME)
