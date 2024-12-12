#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


class UserNotFound(Exception):
    pass


class GroupNotFound(Exception):
    pass


class UserSessionNotFound(Exception):
    pass


class ServerNotFound(Exception):
    pass


class SettingNotFound(Exception):
    pass


class SessionPermissionsNotFound(Exception):
    pass


class PermissionProfileNotFound(Exception):
    pass


class SoftwareStackNotFound(Exception):
    pass


class InvalidParams(Exception):
    pass


class EmailTemplateNotFound(Exception):
    pass


class UnauthorizedAccess(Exception):
    def __init__(self, error_code: str, message: str = None):
        self._error_code = error_code
        self._message = message


class AuthTokenExpired(Exception):
    def __init__(self, error_code: str, message: str = None):
        self._error_code = error_code
        self._message = message


class BadRequest(Exception):
    def __init__(self, error_code: str = "400", message: str = "Bad Request"):
        self._error_code = error_code
        self._message = message


# AD Sync
class ADSyncConfigurationNotFound(Exception):
    pass


class ADSyncInProcess(Exception):
    pass
