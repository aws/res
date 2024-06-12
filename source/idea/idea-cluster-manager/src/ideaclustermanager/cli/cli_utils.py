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
import csv
import os.path

from ideasdk.context import SocaCliContext
from ideasdk.utils import Utils
from ideadatamodel import (
    User,
    CreateUserRequest,
    CreateUserResult,
    GetUserRequest,
    GetUserResult,
    constants,
    errorcodes,
    exceptions
)
from ideaclustermanager.app.accounts.auth_utils import AuthUtils
from rich.table import Table

from typing import List
import time
import re

API_CONTEXT_PATH_CLUSTER_MANAGER = '/cluster-manager/api/v1'


class ClusterManagerUtils:

    @staticmethod
    def get_soca_cli_context_cluster_manager() -> SocaCliContext:
        return SocaCliContext(api_context_path=API_CONTEXT_PATH_CLUSTER_MANAGER)

    @staticmethod
    def check_duplicate_users_in_csv(usernames: List[str]) -> List[str]:
        seen = set()
        duplicates = []

        for username in usernames:
            if username in seen:
                duplicates.append(username)
            else:
                seen.add(username)

        return duplicates

    @staticmethod
    def check_duplicate_users(usernames: List[str], context: SocaCliContext) -> List[str]:

        duplicates = []

        for username in usernames:
            result = None
            try:
                # calling get user to see if username already exists
                result = context.unix_socket_client.invoke_alt(
                    namespace='Accounts.GetUser',
                    payload=GetUserRequest(
                        username=username
                    ),
                    result_as=GetUserResult
                )
            except exceptions.SocaException as e:
                # If error code == AUTH_USER_NOT_FOUND, we have a new user, continue flow
                if e.error_code != errorcodes.AUTH_USER_NOT_FOUND:
                    raise e
            except Exception as e:
                raise e

            # username already exists
            if result is not None:
                duplicates.append(username)

        return duplicates

    @staticmethod
    def create_users(users: List[User], context: SocaCliContext) -> [(User, str)]:

        create_users_response = []

        if users is None or len(users) == 0:
            return create_users_response

        for entry in users:
            try:
                context.unix_socket_client.invoke_alt(
                    namespace='Accounts.CreateUser',
                    payload=CreateUserRequest(
                        user=entry
                    ),
                    result_as=CreateUserResult
                )
                response_entry = (entry, 'n/a')
            except Exception as e:
                response_entry = (entry, f'{e}')

            create_users_response.append(response_entry)

        return create_users_response

    @staticmethod
    def print_create_user_status(users: [(User, str)], context: SocaCliContext):

        num_tries = 0
        while True:
            all_done = True
            table = ClusterManagerUtils.build_create_user_status_table()
            for entry in users:
                if Utils.are_equal(entry[1], 'n/a'):
                    response = context.shell.invoke(cmd=f'id {entry[0].username}', shell=True)
                    if response.returncode == 0:
                        table.add_row(entry[0].username, entry[0].email, Utils.get_as_string(entry[0].sudo, default='False'), 'SUCCESS', 'n/a', style='green')
                    else:
                        table.add_row(entry[0].username, entry[0].email, Utils.get_value_as_string(entry[0].sudo, default='False'), 'IN PROGRESS', 'n/a')
                        all_done = False
                else:
                    table.add_row(entry[0].username, entry[0].email, Utils.get_value_as_string(entry[0].sudo, default='False'), 'FAILED', entry[1], style='red')
            context.print(table)

            if all_done or num_tries == 10:
                break
            else:
                num_tries += 1
                time.sleep(30)

    @staticmethod
    def check_has_valid_csv_headers(headers, context: SocaCliContext):
        if len(headers) < 2 or len(headers) > 3:
            context.error('Incorrect number of columns provided; run with --generate-template to see an example')
            raise SystemExit(1)
        elif len(headers) == 2:
            if 'Username' not in headers or 'Email' not in headers:
                context.error('"Username" and "Email" fields must be provided in the header; "Is Admin?" is optional; run with --generate-template to see an example')
                raise SystemExit(1)
        elif len(headers) == 3:
            if 'Username' not in headers or 'Email' not in headers or 'Is Admin?' not in headers:
                context.error('"Username" and "Email" fields must be provided in the header; "Is Admin?" is optional; run with --generate-template to see an example')
                raise SystemExit(1)

    @staticmethod
    def check_if_csv_file(filepath: str, context: SocaCliContext):
        if not Utils.is_file(filepath):
            context.error(f'This path {filepath} is not a file; Please provide a csv file')
            raise SystemExit(1)
        elif not filepath.endswith('.csv'):
            context.error(f'This file: {filepath} is not a csv file; Please provide a csv file')
            raise SystemExit(1)

    @staticmethod
    def generate_template(path: str) -> str:

        csv_file = os.path.join(path, 'users_file_template.csv')
        header = ['Username', 'Email', 'Is Admin?']

        with open(csv_file, 'w', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(header)

        return csv_file

    @staticmethod
    def check_valid_username(username: str):
        if Utils.is_empty(username):
            raise exceptions.invalid_params("username is required")
        elif not re.match(constants.USERNAME_REGEX, username):
            raise exceptions.invalid_params(constants.USERNAME_ERROR_MESSAGE)
        elif username.strip().lower() in ('admin', 'administrator'):
            raise exceptions.invalid_params(f'invalid username: {username}. Change username to prevent conflicts with local or directory system users.')

    @staticmethod
    def check_valid_email(email: str):
        try:
            AuthUtils.sanitize_email(email)
        except exceptions.SocaException as e:
            raise e

    @staticmethod
    def build_create_user_status_table() -> Table:

        status_table = Table()
        status_table.add_column('Username', justify='left', no_wrap=False)
        status_table.add_column('Email', justify='left', no_wrap=False)
        status_table.add_column('Is Admin?', justify='left', no_wrap=False)
        status_table.add_column('Status', justify='left', no_wrap=False)
        status_table.add_column('Reason', justify='left', no_wrap=False)

        return status_table

    @staticmethod
    def build_confirm_user_table() -> Table:

        confirm_table = Table()
        confirm_table.add_column('Username', justify='left', no_wrap=False)
        confirm_table.add_column('Email', justify='left', no_wrap=False)
        confirm_table.add_column('Is Admin?', justify='left', no_wrap=False)

        return confirm_table
