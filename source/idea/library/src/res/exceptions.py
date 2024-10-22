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
