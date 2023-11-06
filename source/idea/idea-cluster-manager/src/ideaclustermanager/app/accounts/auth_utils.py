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

from ideasdk.utils import Utils
from ideadatamodel import exceptions, errorcodes, constants

import validators


class AuthUtils:

    @staticmethod
    def sanitize_username(username: str) -> str:
        if Utils.is_empty(username):
            raise exceptions.invalid_params('username is required')
        return username.strip().lower()

    @staticmethod
    def sanitize_email(email: str) -> str:
        if Utils.is_empty(email):
            raise exceptions.invalid_params('email is required')

        email = email.strip().lower()

        if not validators.email(email):
            raise exceptions.invalid_params(f'invalid email: {email}')

        return email

    @staticmethod
    def sanitize_sub(sub: str) -> str:
        if Utils.is_empty(sub):
            raise exceptions.invalid_params('sub is required')

        sub = sub.strip().lower()

        if not validators.uuid(sub):
            raise exceptions.invalid_params(f'invalid sub(expected UUID): {sub}')

        return sub

    @staticmethod
    def invalid_operation(message: str) -> exceptions.SocaException:
        return exceptions.SocaException(
            error_code=errorcodes.AUTH_INVALID_OPERATION,
            message=message
        )

    @staticmethod
    def check_allowed_username(username: str):
        if username.strip().lower() in ('root',
                                        'admin',
                                        'administrator',
                                        constants.IDEA_SERVICE_ACCOUNT,
                                        'ec2-user',
                                        'centos',
                                        'ssm-user'):
            raise exceptions.invalid_params(f'invalid username: {username}. Change username to prevent conflicts with local or directory system users.')
