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
from ideadatamodel import (
    exceptions, errorcodes
)
from ideadatamodel import (
    SubmitJobResult,
    SubmitJobRequest,
    GetJobRequest,
    GetJobResult,
    ReadFileRequest,
    ReadFileResult
)

import ideaadministrator
from ideaadministrator.integration_tests.test_context import TestContext

import os
from typing import Dict, Optional
import arrow
import re
import time
import random


class JobTestCase:

    def __init__(self, helper: 'JobSubmissionHelper', test_case_id: str, base_os: str, ami_id: str, test_case_config: Dict):
        self.helper = helper
        self.context = helper.context
        self.test_case_id = test_case_id
        self.test_case_config = test_case_config
        self.base_os = base_os
        resources = Utils.get_value_as_string('resource', test_case_config)
        self.resources = f'{resources},instance_ami={ami_id},base_os={base_os}'
        self.command = Utils.get_value_as_string('command', test_case_config)
        if ';' in self.command:
            self.command = f'{{ {self.command} }}'

        self.expected_output = Utils.get_value_as_string('expected_output', test_case_config)
        if self.expected_output:
            self.expected_output = self.expected_output.strip()

        self.regex_match = Utils.get_value_as_bool('regex_match', test_case_config, False)
        self.expected_error_code = Utils.get_value_as_string('error_code', test_case_config)
        self.queue = Utils.get_value_as_string('queue', test_case_config)
        self.job_group = Utils.get_value_as_string('job_group', test_case_config)

        self.status = 'PENDING'
        self.exception = None
        self.actual_output = None
        self.job_submit_result: Optional[SubmitJobResult] = None
        self.output_folder = f'/home/{self.context.admin_username}/integration-tests/{helper.context.test_run_id}'
        self.output_file = f'{self.output_folder}/{self.test_case_id}.log'
        self.message: Optional[str] = None
        self.submission_time: Optional[arrow.Arrow] = None
        self.max_dry_run_attempts = 10
        self.dry_run_attempt = 0
        self.subnets = self.context.cluster_config.get_list('cluster.network.private_subnets', required=True)
        # Subnets that we have previously attempted/failed (EC2 DryRun failure)
        self.invalid_subnets = set()

    def submit_job(self):
        _potential_subnets = [x for x in self.subnets if x not in self.invalid_subnets]
        if self.dry_run_attempt > 0:
            self.context.info(f'submit_job() - {self.test_case_id} - Subnets: {self.subnets}  Invalid_Subnets: {self.invalid_subnets} _potential_subnets = {_potential_subnets} ReAttempt: {self.dry_run_attempt}')
        # No subnets passed the self.invalid_subnets filter - error this TestCaseId
        if not _potential_subnets:
            self.status = 'FAIL'
            self.context.error(f'Failed to Submit Job for TestCaseId: {self.test_case_id} - ERROR: Exhausted all potential subnets.')

        subnet_id = random.choice(_potential_subnets)
        job_script = f"""#!/bin/bash
#PBS -N {self.test_case_id}
#PBS -q {self.queue}
#PBS -l {self.resources}
#PBS -l subnet_id={subnet_id}
#PBS -P default
mkdir -p {self.output_folder}
{self.command} > {self.output_file}
        """
        try:
            result = self.context.get_scheduler_client().invoke_alt(
                namespace='Scheduler.SubmitJob',
                payload=SubmitJobRequest(
                    job_script_interpreter='pbs',
                    job_script=Utils.base64_encode(job_script)
                ),
                result_as=SubmitJobResult,
                access_token=self.context.get_admin_access_token()
            )
            self.job_submit_result = result
            self.status = 'IN_PROGRESS'
            self.submission_time = arrow.get()
            self.context.info(f'submit_job() - Job submitted for TestCaseId: {self.test_case_id} on subnet_id {subnet_id} Retry: {self.dry_run_attempt}')

        except exceptions.SocaException as e:
            self.context.info(f'submit_job() - SOCA Exception: {e}')
            if Utils.is_not_empty(self.expected_error_code) and e.error_code == self.expected_error_code:
                if Utils.is_not_empty(self.expected_output):
                    if self.expected_output in e.message:
                        self.status = 'PASS'
                    else:
                        self.status = 'FAIL'
                else:
                    self.status = 'PASS'
            else:
                self.exception = e
                self.status = 'AUTO_RETRY'
                if 'EC2DryRunFailed' in e.message:
                    self.context.info(f'submit_job() - Encountered DryRun failure for {self.test_case_id}')
                    while self.dry_run_attempt < self.max_dry_run_attempts and self.status != 'IN_PROGRESS':
                        self.dry_run_attempt += 1
                        if subnet_id not in self.invalid_subnets:
                            self.context.warning(f'submit_job() - Adding subnet_id {subnet_id} as an invalid_subnet')
                            self.invalid_subnets.add(subnet_id)
                        else:
                            self.context.warning(f'submit_job() - Subnet_id {subnet_id} already in invalid_subnets set. This Should not happen.')

                        self.context.warning(f'submit_job() - TestCaseId: {self.test_case_id} / {subnet_id}. Retry in 15 secs using a different subnet_id Invalid_subnets: {self.invalid_subnets} [Loop: {self.dry_run_attempt}/{self.max_dry_run_attempts}]')

                        time.sleep(15)
                        # Clear the old exception and try again
                        self.exception = None
                        self.status = 'PENDING'
                        self.submit_job()
                else:
                    self.status = 'FAIL'
                    self.context.error(f'Failed to Submit Job for TestCaseId: {self.test_case_id} - Unknown exception: {e}')
        except Exception as e:
            self.status = 'FAIL'
            self.exception = e
            self.context.error(f'Failed to Submit Job for TestCaseId: {self.test_case_id} - Exception: {e}')

    def get_job_id(self) -> str:
        if self.job_submit_result and self.job_submit_result.job:
            return self.job_submit_result.job.job_id
        return 'UNKNOWN'

    def check_progress(self):
        try:
            self.context.get_scheduler_client().invoke_alt(
                namespace='Scheduler.GetCompletedJob',
                payload=GetJobRequest(
                    job_id=self.job_submit_result.job.job_id
                ),
                result_as=GetJobResult,
                access_token=self.context.get_admin_access_token()
            )
            self.status = 'COMPLETE'
        except exceptions.SocaException as e:
            if e.error_code == errorcodes.JOB_NOT_FOUND:
                self.status = 'IN_PROGRESS'
            else:
                raise e

    def get_output(self) -> str:
        read_file_result = self.context.get_cluster_manager_client().invoke_alt(
            namespace='FileBrowser.ReadFile',
            payload=ReadFileRequest(
                file=self.output_file
            ),
            result_as=ReadFileResult,
            access_token=self.context.get_admin_access_token()
        )
        return Utils.base64_decode(read_file_result.content).strip()

    def verify_output(self):
        try:
            self.actual_output = self.get_output()
            if self.regex_match:
                success = re.match(self.expected_output, self.actual_output)
            else:
                success = self.expected_output in self.actual_output

            if success:
                self.status = 'PASS'
                self.context.success(f'Job TestCaseId: {self.test_case_id}  {self.expected_output} == {self.actual_output}          [PASS]')
            else:
                self.status = 'FAIL'
                self.context.error(f'Job TestCaseId: {self.test_case_id}  {self.expected_output} != {self.actual_output}          [FAIL]')

        except Exception as e:
            self.status = 'FAIL'
            self.exception = e


class JobSubmissionHelper:

    def __init__(self, context: TestContext):

        self.context = context
        self.job_test_case_config = self.read_job_test_case_config()
        self.job_test_cases: Dict[str, JobTestCase] = {}

    @staticmethod
    def read_job_test_case_config():
        resources_dir = ideaadministrator.props.resources_dir
        test_cases_file = os.path.join(resources_dir, 'integration_tests', 'job_test_cases.yml')
        with open(test_cases_file, 'r') as f:
            return Utils.from_yaml(f.read())

    def get_ami_id(self, base_os: str) -> Optional[str]:
        base_os_param = self.context.extra_params.get('base_os')
        if Utils.is_not_empty(base_os_param):
            tokens = base_os_param.split(',')
            for token in tokens:
                kv = token.split(':')
                if len(kv) == 2:
                    provided_base_os = kv[0].strip()
                    ami_id = kv[1].strip()
                    if Utils.is_not_empty(ami_id) and base_os == provided_base_os:
                        return ami_id

        compute_node_os = self.context.cluster_config.get_string('scheduler.compute_node_os', required=True)
        if base_os == compute_node_os:
            return self.context.cluster_config.get_string('scheduler.compute_node_ami', required=True)

        regions_config_file = ideaadministrator.props.region_ami_config_file()
        with open(regions_config_file, 'r') as f:
            regions_config = Utils.from_yaml(f.read())
        ami_config = Utils.get_value_as_dict(self.context.aws_region, regions_config)
        if ami_config is None:
            raise exceptions.general_exception(f'aws_region: {self.context.aws_region} not found in region_ami_config.yml')
        ami_id = Utils.get_value_as_string(base_os, ami_config)
        if Utils.is_empty(ami_id):
            raise exceptions.general_exception(f'instance_ami not found for base_os: {base_os}, region: {self.context.aws_region}')
        return ami_id

    def get_test_case_config(self, name: str) -> Dict:
        all_test_case_configs = Utils.get_value_as_list('test_cases', self.job_test_case_config)

        for test_case_config in all_test_case_configs:

            current_test_case_name = Utils.get_value_as_string('name', test_case_config)

            if current_test_case_name != name:
                continue

            return test_case_config

    def get_or_create_test_case(self, name: str, base_os: str) -> JobTestCase:
        test_case_id = f'{base_os}_{name}'
        if test_case_id in self.job_test_cases:
            return self.job_test_cases[test_case_id]

        ami_id = self.get_ami_id(base_os)
        test_case_config = self.get_test_case_config(name)

        job_test_case = JobTestCase(
            helper=self,
            test_case_id=test_case_id,
            base_os=base_os,
            ami_id=ami_id,
            test_case_config=test_case_config
        )
        self.job_test_cases[test_case_id] = job_test_case
        return job_test_case

    def submit_job(self, name: str, base_os: str) -> JobTestCase:
        """
        fetches the test case config and submits the job if not already submitted
        :param name: name of the test case
        :param base_os: one of the supported base os name
        :return:
        """
        test_case = self.get_or_create_test_case(name, base_os)
        if test_case.status == 'PENDING':
            test_case.submit_job()
        return test_case

    def get_test_case_count(self) -> int:
        return len(self.job_test_cases)

    def get_success_count(self) -> int:
        result = 0
        for test_case_id in self.job_test_cases:
            test_case = self.job_test_cases[test_case_id]
            if test_case.status == 'PASS':
                result += 1
        return result

    def get_failed_count(self) -> int:
        result = 0
        for test_case_id in self.job_test_cases:
            test_case = self.job_test_cases[test_case_id]
            if test_case.status == 'FAIL':
                result += 1
        return result

    def get_completed_count(self) -> int:
        result = 0
        for test_case_id in self.job_test_cases:
            test_case = self.job_test_cases[test_case_id]
            if test_case.status in ('PASS', 'FAIL'):
                result += 1
        return result

    def get_in_progress_count(self) -> int:
        result = 0
        for test_case_id in self.job_test_cases:
            test_case = self.job_test_cases[test_case_id]
            if test_case.status == 'IN_PROGRESS':
                result += 1
        return result

    def print_summary(self, header: str):
        self.context.idea_context.print_title(
            f'[RunId: {self.context.test_run_id}] {header}: '
            f'Total: {self.get_test_case_count()}, '
            f'Completed: {self.get_completed_count()}, '
            f'Success: {self.get_success_count()}, '
            f'Failed: {self.get_failed_count()}')
        print('{:100s} {:10s} {:20s}'.format('Job Test Case Id', 'Job Id', 'Status'))
        for test_case_id in self.job_test_cases:
            test_case = self.job_test_cases[test_case_id]
            print('{:100s} {:10s} {:20s}'.format(test_case_id, test_case.get_job_id(), test_case.status))

