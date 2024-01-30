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
Test Cases for ApiAuthorizationService
"""

import unittest
from typing import Optional

import pytest
from _pytest.monkeypatch import MonkeyPatch
from ideaclustermanager import AppContext
from ideaclustermanager.app.auth.api_authorization_service import (
    ClusterManagerApiAuthorizationService,
)

from ideadatamodel import User, constants
from ideadatamodel.api.api_model import ApiAuthorizationType


@pytest.fixture(scope="class")
def monkeypatch_for_class(request):
    request.cls.monkeypatch = MonkeyPatch()


@pytest.fixture(scope="class")
def context_for_class(request, context):
    request.cls.context = context


@pytest.mark.usefixtures("monkeypatch_for_class")
@pytest.mark.usefixtures("context_for_class")
class ApiAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.admin_username = "dummy_admin"
        self.admin_email = self.admin_username + "@email.com"
        self.monkeypatch.setattr(
            self.context.accounts.sssd, "ldap_id_mapping", lambda x: "False"
        )
        self.monkeypatch.setattr(
            self.context.accounts.sssd,
            "get_uid_and_gid_for_user",
            lambda x: (1000, 1000),
        )
        self.context.accounts.create_user(
            user=User(
                username=self.admin_username,
                email=self.admin_email,
                role=constants.ADMIN_ROLE,
            ),
        )

        self.user_username = "dummy_user"
        self.user_email = self.user_username + "@email.com"
        self.context.accounts.create_user(
            user=User(
                username=self.user_username,
                email=self.user_email,
                role=constants.USER_ROLE,
            ),
        )

    def test_api_auth_service_get_authorization_app_passes(self):
        token = {
            "username": "",
        }
        api_authorization = self.context.api_authorization_service.get_authorization(
            token
        )
        assert api_authorization.type == ApiAuthorizationType.APP
        assert not api_authorization.username

    def test_api_auth_service_get_authorization_admin_passes(self):
        token = {"username": self.admin_username}
        api_authorization = self.context.api_authorization_service.get_authorization(
            token
        )
        assert api_authorization.type == ApiAuthorizationType.ADMINISTRATOR
        assert api_authorization.username == self.admin_username

    def test_api_auth_service_get_authorization_user_passes(self):
        token = {"username": self.user_username}
        api_authorization = self.context.api_authorization_service.get_authorization(
            token
        )
        assert api_authorization.type == ApiAuthorizationType.USER
        assert api_authorization.username == self.user_username

    def tearDown(self):
        self.context.accounts.delete_user(self.admin_username)
        self.context.accounts.delete_user(self.user_username)
