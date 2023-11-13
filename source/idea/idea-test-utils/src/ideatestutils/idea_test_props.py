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

import os


class IdeaTestProps:

    def get_idea_user_home_dir(self) -> str:
        idea_user_home = os.environ.get('IDEA_USER_HOME', os.path.expanduser(os.path.join('~', '.idea')))
        os.makedirs(idea_user_home, exist_ok=True)
        return idea_user_home

    def get_test_home_dir(self) -> str:
        idea_user_home = self.get_idea_user_home_dir()
        test_home = os.path.join(idea_user_home, 'tests')
        os.makedirs(test_home, exist_ok=True)
        return test_home

    def get_test_dir(self, name: str) -> str:
        test_home_dir = self.get_test_home_dir()
        test_dir = os.path.join(test_home_dir, name)
        os.makedirs(test_dir, exist_ok=True)
        return test_dir

    def get_non_existent_username(self) -> str:
        return "nonexistent"
