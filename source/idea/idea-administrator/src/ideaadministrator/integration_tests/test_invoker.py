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

from ideadatamodel import constants, exceptions, errorcodes

from ideaadministrator.integration_tests.test_context import TestContext
from ideaadministrator.integration_tests import cluster_manager_tests
from ideaadministrator.integration_tests import scheduler_tests, virtual_desktop_controller_tests

from typing import List
import traceback


class TestInvoker:
    def __init__(self, test_context: TestContext, module_ids: List[str]):
        self.test_context = test_context
        self.module_ids = module_ids

        self.module_test_cases = {
            constants.MODULE_CLUSTER_MANAGER: cluster_manager_tests.TEST_CASES,
            constants.MODULE_SCHEDULER: scheduler_tests.TEST_CASES,
            constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER: virtual_desktop_controller_tests.TEST_CASES
        }

    def invoke(self):
        for module_id in self.module_ids:

            # set current module_id in cluster config so that module setting keys for
            # module test cases are resolved correctly
            self.test_context.cluster_config.set_module_id(module_id)

            module_info = self.test_context.cluster_config.module_info
            module_status = module_info['status']
            if module_status != 'deployed':
                raise exceptions.general_exception(f'module id: {module_id} is not deployed yet.')

            module_name = module_info['name']

            test_cases = self.module_test_cases.get(module_name)
            if test_cases is None:
                self.test_context.warning(f'no test cases found for module: {module_name}')
                continue

            total_count = 0
            fail_count = 0
            success_count = 0
            for test_case in test_cases:
                test_case_id = test_case['test_case_id']
                test_case_fn = test_case['test_case']

                if self.test_context.filter_test_case_ids is not None:
                    if test_case_id not in self.test_context.filter_test_case_ids:
                        continue

                try:

                    total_count += 1

                    self.test_context.begin_test_case(test_case_id)
                    test_case_fn(context=self.test_context)
                    self.test_context.end_test_case(test_case_id, True)

                    success_count += 1

                except Exception as e:
                    print(e)
                    if self.test_context.debug:
                        traceback.print_exc()
                    self.test_context.end_test_case(test_case_id, False)

                    fail_count += 1

            if fail_count > 0:
                success_percent = (success_count / total_count) * 100
                raise exceptions.soca_exception(
                    error_code=errorcodes.INTEGRATION_TEST_FAILED,
                    message=f'{fail_count} of {total_count} test cases failed. success rate: {round(success_percent, 2)}%'
                )
