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
from res.resources import accounts

from ideadatamodel import User, constants, exceptions
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
            accounts,
            "_get_uid_and_gid_for_username",
            lambda x: (1000, 1000),
        )
        accounts.create_user(
            {
                "username": self.admin_username,
                "email": self.admin_email,
                "role": constants.ADMIN_ROLE,
                "identity_source": constants.SSO_USER_IDP_TYPE,
            },
        )

        self.user_username = "dummy_user"
        self.user_email = self.user_username + "@email.com"
        accounts.create_user(
            {
                "username": self.user_username,
                "email": self.user_email,
                "role": constants.USER_ROLE,
                "identity_source": constants.SSO_USER_IDP_TYPE,
            },
        )

        self.user_sso_disabled_username = "dummy_user_no_sso"
        self.user_sso_disabled_email = self.user_sso_disabled_username + "@email.com"
        accounts.create_user(
            {
                "username": self.user_sso_disabled_username,
                "email": self.user_sso_disabled_email,
                "role": constants.USER_ROLE,
                "identity_source": constants.SSO_USER_IDP_TYPE,
            },
        )

        self.user_native_auth_disabled_username = "dummy_user_no_native"
        self.user_native_auth_disabled_email = (
            self.user_native_auth_disabled_username + "@email.com"
        )
        accounts.create_user(
            {
                "username": self.user_native_auth_disabled_username,
                "email": self.user_native_auth_disabled_email,
                "role": constants.USER_ROLE,
                "identity_source": constants.COGNITO_USER_IDP_TYPE,
            },
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
        self.monkeypatch.setattr(
            self.context.api_authorization_service.config,
            "get_bool",
            lambda x, required=False: "True",
        )
        api_authorization = self.context.api_authorization_service.get_authorization(
            token
        )
        assert api_authorization.type == ApiAuthorizationType.ADMINISTRATOR
        assert api_authorization.username == self.admin_username

    def test_api_auth_service_get_authorization_user_passes(self):
        token = {"username": self.user_username}
        self.monkeypatch.setattr(
            self.context.api_authorization_service.config,
            "get_bool",
            lambda x, required=False: "True",
        )
        api_authorization = self.context.api_authorization_service.get_authorization(
            token
        )
        assert api_authorization.type == ApiAuthorizationType.USER
        assert api_authorization.username == self.user_username

    def test_api_auth_service_sso_disabled_fail(self):
        token = {"username": self.user_sso_disabled_username}
        with pytest.raises(exceptions.SocaException):
            api_authorization = (
                self.context.api_authorization_service.get_authorization(token)
            )

    def test_api_auth_service_native_auth_disabled_fail(self):
        self.monkeypatch.setattr(
            self.context.api_authorization_service.config,
            "get_bool",
            lambda x, required=False: False,
        )
        token = {"username": self.user_native_auth_disabled_username}
        with pytest.raises(exceptions.SocaException):
            api_authorization = (
                self.context.api_authorization_service.get_authorization(token)
            )

    def tearDown(self):
        accounts.delete_user({"username": self.admin_username})
        accounts.delete_user({"username": self.user_username})
        accounts.delete_user({"username": self.user_sso_disabled_username})
        accounts.delete_user({"username": self.user_native_auth_disabled_username})

        self.monkeypatch.undo()
