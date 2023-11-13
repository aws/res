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

from ideasdk.utils import Utils, GroupNameHelper
from ideadatamodel import (
    exceptions, errorcodes
)
from ideadatamodel import (
    HpcQueueProfile,
    CreateProjectRequest,
    CreateProjectResult,
    Project,
    SocaKeyValue,
    CreateQueueProfileRequest,
    CreateQueueProfileResult,
    SocaQueueMode,
    SocaJobParams,
    SocaScalingMode,
    EnableQueueProfileRequest,
    ListQueueProfilesRequest,
    ListQueueProfilesResult,
    SubmitJobRequest,
    SubmitJobResult,
    DisableQueueProfileRequest,
    DeleteQueueProfileRequest
)

from ideaadministrator.integration_tests.test_context import TestContext
from ideaadministrator.integration_tests import test_constants
from ideaadministrator.integration_tests.scheduler.job_test_case import JobSubmissionHelper

from typing import Optional, List
import time


TEST_PROJECT_ID: Optional[str] = None


def _submit_all_jobs(context: TestContext, helper: JobSubmissionHelper, base_os_names: List[str], test_case_filter: List[str]):
    all_test_case_configs = Utils.get_value_as_list('test_cases', helper.job_test_case_config)
    job_region = context.cluster_config.get_string('cluster.aws.region')
    job_submission_count = 0
    for base_os in base_os_names:
        for test_case_config in all_test_case_configs:

            # check if test case can be skipped
            skip_regions = Utils.get_value_as_list('skip_regions', test_case_config)
            if skip_regions:
                if job_region in skip_regions or "all" in skip_regions:
                    continue

            name = Utils.get_value_as_string('name', test_case_config)
            if Utils.is_not_empty(test_case_filter):
                if name in test_case_filter:
                    helper.submit_job(name, base_os)
                    job_submission_count += 1
            else:
                helper.submit_job(name, base_os)
                job_submission_count += 1

    helper.context.info(f'Job Test Cases - Submitted {job_submission_count} Jobs.')


def _verify_all_jobs(helper: JobSubmissionHelper):
    try:
        helper.context.info('Job Test Cases - Start Job Validations ...')

        iteration_interval = 60
        max_iterations = 30
        current_iteration = 0

        while current_iteration <= max_iterations:

            current_iteration += 1

            for test_case_id in helper.job_test_cases:
                test_case = helper.job_test_cases[test_case_id]
                try:

                    if test_case.status in ('PASS', 'FAIL'):
                        continue

                    test_case.check_progress()
                    if test_case.status == 'IN_PROGRESS':
                        continue

                    if test_case.status == 'COMPLETE':
                        test_case.verify_output()

                except Exception as e:
                    helper.context.error(f'failed to verify status for TestCaseId: {test_case.test_case_id} - {e}')

            helper.print_summary('Job Test Case Progress')

            if helper.get_completed_count() >= helper.get_test_case_count():
                break

            helper.context.info(f'[{current_iteration} of {max_iterations}] Sleeping for {iteration_interval} seconds')
            time.sleep(iteration_interval)
    except KeyboardInterrupt:
        helper.context.error('Job test case verification aborted!')


def test_jobs(context: TestContext):
    base_os_param = context.extra_params.get('base_os')
    if Utils.is_empty(base_os_param):
        base_os_names = [context.cluster_config.get_string('scheduler.compute_node_os')]
    else:
        tokens = base_os_param.split(',')
        base_os_names = []
        for token in tokens:
            base_os_names.append(token.split(':')[0].strip())

    job_filter_string = context.extra_params.get('job_test_cases')
    if Utils.is_empty(job_filter_string):
        job_filters = []
    else:
        job_filters = job_filter_string.split(',')

    helper = JobSubmissionHelper(
        context=context
    )
    _submit_all_jobs(context, helper, base_os_names, job_filters)
    _verify_all_jobs(helper)

    # shared job verifications. ensure that test cases with same job group execute on the same host
    job_groups = {}
    for job_test_case_id in helper.job_test_cases:
        test_case = helper.job_test_cases[job_test_case_id]
        if test_case.job_group is None:
            continue

        job_shared_test_case = helper.job_test_cases[job_test_case_id]
        job_group_key = f'{job_shared_test_case.base_os}.{job_shared_test_case.job_group}'

        if job_group_key in job_groups:
            jobs = job_groups[job_group_key]
        else:
            jobs = []
            job_groups[job_group_key] = jobs

        jobs.append(test_case)

    result = helper.get_success_count() == helper.get_test_case_count()
    if len(job_groups) > 0:
        for job_group_key in job_groups:
            jobs = job_groups[job_group_key]
            if len(jobs) < 2:
                continue
            if jobs[0].actual_output != jobs[1].actual_output:
                jobs[0].status = 'FAIL'
                jobs[1].status = 'FAIL'
                result = False

    helper.print_summary('Job Test Case Summary')
    assert result


def test_admin_queue_profiles(context: TestContext):
    created_queue_profile: Optional[HpcQueueProfile] = None

    try:

        test_queue_profile_name = Utils.generate_password(8, 0, 8, 0, 0)

        # Create project to associate to the queue
        queue_profile_project = context.get_cluster_manager_client().invoke_alt(
            namespace='Projects.CreateProject',
            payload=CreateProjectRequest(
                project=Project(
                    name=test_queue_profile_name,
                    title=f'{test_queue_profile_name} title',
                    description=f'{test_queue_profile_name} description',
                    ldap_groups=[GroupNameHelper(context.idea_context).get_default_project_group()],
                    tags=[
                        SocaKeyValue(key='key', value='value')
                    ]
                )
            ),
            result_as=CreateProjectResult,
            access_token=context.get_admin_access_token()
        )

        # create queue profile
        context.info(f'Create Queue Profile: {test_queue_profile_name}')
        create_queue_profile_result = context.get_scheduler_client().invoke_alt(
            namespace='SchedulerAdmin.CreateQueueProfile',
            payload=CreateQueueProfileRequest(
                queue_profile=HpcQueueProfile(
                    title='Integration Test Queue Profile',
                    name=test_queue_profile_name,
                    description='Test Queue Profile - Description',
                    queues=[test_queue_profile_name],
                    queue_mode=SocaQueueMode.FIFO,
                    projects=[queue_profile_project.project],
                    scaling_mode=SocaScalingMode.SINGLE_JOB,
                    terminate_when_idle=0,
                    keep_forever=False,
                    default_job_params=SocaJobParams(
                        instance_types=['c5.large'],
                        base_os=context.cluster_config.get_string('scheduler.compute_node_os', required=True),
                        instance_ami=context.cluster_config.get_string('scheduler.compute_node_ami', required=True)
                    )
                )
            ),
            result_as=CreateQueueProfileResult,
            access_token=context.get_admin_access_token()
        )

        queue_profile = create_queue_profile_result.queue_profile
        assert queue_profile is not None
        assert queue_profile.queue_profile_id is not None
        assert queue_profile.enabled is False

        created_queue_profile = queue_profile

        # enable queue profile
        context.info(f'Enable Queue Profile: {test_queue_profile_name}')
        context.get_scheduler_client().invoke_alt(
            namespace='SchedulerAdmin.EnableQueueProfile',
            payload=EnableQueueProfileRequest(
                queue_profile_name=queue_profile.name
            ),
            access_token=context.get_admin_access_token()
        )

        # list queue profiles
        context.info('Listing Queue Profiles')
        list_queue_profiles_result = context.get_scheduler_client().invoke_alt(
            namespace='SchedulerAdmin.ListQueueProfiles',
            payload=ListQueueProfilesRequest(),
            result_as=ListQueueProfilesResult,
            access_token=context.get_admin_access_token()
        )
        assert list_queue_profiles_result.listing is not None
        assert len(list_queue_profiles_result.listing) > 0
        found = False
        for current_queue_profile in list_queue_profiles_result.listing:
            if current_queue_profile.queue_profile_id == created_queue_profile.queue_profile_id:
                context.info(f'Found Queue Profile: {test_queue_profile_name} in listing response')
                found = True
        assert found is True

        # dry run submit job
        context.info(f'Submit DryRun Job on Queue Profile: {test_queue_profile_name}')
        job_script_valid = f"""#!/bin/bash
#PBS -N queue_profile_test
#PBS -q {test_queue_profile_name}
#PBS -P default
/bin/echo test
        """
        submit_job_result = context.get_scheduler_client().invoke_alt(
            namespace='Scheduler.SubmitJob',
            payload=SubmitJobRequest(
                job_script_interpreter='pbs',
                job_script=Utils.base64_encode(job_script_valid),
                dry_run=True
            ),
            result_as=SubmitJobResult,
            access_token=context.get_admin_access_token()
        )

        assert len(submit_job_result.validations.results) == 0

        job_script_invalid_project = f"""#!/bin/bash
#PBS -N queue_profile_test
#PBS -q {test_queue_profile_name}
#PBS -P PROJECT_DOES_NOT_EXIST
/bin/echo test
        """
        try:
            context.get_scheduler_client().invoke_alt(
                namespace='Scheduler.SubmitJob',
                payload=SubmitJobRequest(
                    job_script_interpreter='pbs',
                    job_script=Utils.base64_encode(job_script_invalid_project)
                ),
                result_as=SubmitJobResult,
                access_token=context.get_admin_access_token()
            )
            assert False
        except exceptions.SocaException as e:
            assert e.error_code == errorcodes.JOB_SUBMISSION_FAILED
            assert 'PROJECT_DOES_NOT_EXIST' in e.message

        # disable queue profile
        context.info(f'Disable Queue Profile: {test_queue_profile_name}')
        context.get_scheduler_client().invoke_alt(
            namespace='SchedulerAdmin.DisableQueueProfile',
            payload=DisableQueueProfileRequest(
                queue_profile_name=queue_profile.name
            ),
            access_token=context.get_admin_access_token()
        )

        # try submit job on disabled queue profile
        try:
            context.get_scheduler_client().invoke_alt(
                namespace='Scheduler.SubmitJob',
                payload=SubmitJobRequest(
                    job_script_interpreter='pbs',
                    job_script=Utils.base64_encode(job_script_valid),
                    dry_run=True
                ),
                result_as=SubmitJobResult,
                access_token=context.get_admin_access_token()
            )
            assert False
        except exceptions.SocaException as e:
            assert e.error_code == 'SCHEDULER_QUEUE_PROFILE_DISABLED'

    finally:

        if created_queue_profile is not None:
            context.info(f'Delete Queue Profile: {created_queue_profile.name}')
            context.get_scheduler_client().invoke_alt(
                namespace='SchedulerAdmin.DeleteQueueProfile',
                payload=DeleteQueueProfileRequest(
                    queue_profile_name=created_queue_profile.name
                ),
                access_token=context.get_admin_access_token()
            )


TEST_CASES = [
    {
        'test_case_id': test_constants.SCHEDULER_ADMIN_QUEUE_PROFILES,
        'test_case': test_admin_queue_profiles
    },
    {
        'test_case_id': test_constants.SCHEDULER_JOB_TEST_CASES,
        'test_case': test_jobs
    }
]
