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

import ideaadministrator

from ideadatamodel import (
    BaseOS,
    constants,
    exceptions,
    CustomFileLoggerParams
)
from ideasdk.utils import Utils, Jinja2Utils
from ideasdk.shell import ShellInvoker
from ideasdk.logging import SocaLogging
from ideasdk.bootstrap import BootstrapPackageBuilder, BootstrapUtils
from ideasdk.config.cluster_config_db import ClusterConfigDB
from ideasdk.config.cluster_config import ClusterConfig
from ideasdk.context import BootstrapContext
from ideasdk.metrics.cloudwatch.cloudwatch_agent_config import CloudWatchAgentLogFileOptions
from ideasdk.aws import AwsClientProvider, AWSClientProviderOptions

from typing import Optional, List, Dict
import os
import shutil
import logging
import arrow


class CdkInvoker:
    """
    CDK Invoker is responsible for:

    1. invoke the CDK App using cdk nodejs binary.
    2. manage and update cluster configurations after a stack is deployed

    CDK is natively written in TypeScript (and ultimately runs in nodejs), and provides ports for other languages.
    For RES, CDK stacks and constructs in Python, which are synthesized to a cloud formation template that are processed by CDK nodejs binary.

    The CDK Invoker class supports CDK invocation for 2 primary use cases:

    1. as an installed app (currently used primarily in Docker Container flows)
        - in this scenario all packages are installed to python's site-packages
        - this makes invocation of cdk easier, where the --app in cdk becomes::

            cdk --app 'res-admin cdk cdk-app --cluster-name res-dev2 --aws-region us-east-1 --module-id bootstrap --module-name bootstrap --deployment-id 700f4b2c-110b-4395-a208-b13874d20ec5 --termination-protection true'

        - `res-admin cdk cdk-app .. ..` synthesizes the cloudformation template and cdk uses the template to deploy the stack

    2. from sources during development (Dev Mode)
        - this flow is a bit tricky as we need to ensure all the source paths of all modules are available when `--app` parameter is passed to CDK.
        - this is addressed using `invoke`, as invoke is used for all dev automation flows.
        - the command to invoke cdk becomes::

            cdk --app 'invoke cli.admin --args base64("cdk cdk-app --cluster-name res-dev2 --aws-region us-east-1 --module-id bootstrap --module-name bootstrap --deployment-id 700f4b2c-110b-4395-a208-b13874d20ec5 --termination-protection true")

        but there are complications in this flow:
            1. invoke is only available in the dev virtual environment. to address this, the invocation os.environ is passed to the
                shell invocation so that the `invoke` is available in PATH.
            2. all CDK related artifacts, logs, outputs should be generated in ~/.idea/clusters/<region>/<cluster-name>/_cdk folder.
                this by design and not a requirement. primarily so that each cluster can retain it's deployment information in once place
                for easier debugging and future reference.
                to achieve this, the implementation changes directory (cd) to _cdk before executing: cdk --app "..."
                when the directory is changed, `invoke` has no clue where to find `invoke` dev automation tasks. to address this,
                a --search-root parameter is added to tell invoke where to find the project sources.

            after 1 and 2, the final invocation command becomes::

                cdk --app 'invoke --search-root "<project-root>" cli.admin --args "base64data"'

    CDK Binary:
    The installation process does not want to rely on the user to install a specific version of the CDK version. rather, the admin-app
    installation takes care of installing the specific CDK version to ~/.idea/lib/idea-cdk

    Developer must install the CDK binary manually to ~/.idea/lib/idea-cdk using::

        mkdir -p ~/.idea/lib/idea-cdk && pushd ~/.idea/lib/idea-cdk
        npm init --force --yes
        npm install aws-cdk@{LATEST_SUPPORTED_VERSION} --save
        popd

    """

    def __init__(self,
                 cluster_name: str,
                 aws_region: str,
                 module_id: str,
                 module_set: str,
                 aws_profile: str = None,
                 deployment_id: str = None,
                 termination_protection: bool = True,
                 rollback: bool = True):

        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.module_id = module_id
        self.aws_profile = aws_profile
        self.termination_protection = termination_protection
        self.rollback = rollback

        if Utils.is_empty(module_set):
            module_set = constants.DEFAULT_MODULE_SET
        self.module_set = module_set

        if Utils.is_empty(deployment_id):
            deployment_id = Utils.uuid()
        self.deployment_id = deployment_id

        # custom file logging to enable exporting deployment logs for debugging and support
        self.logging = SocaLogging()
        cluster_logs_dir = ideaadministrator.props.cluster_logs_dir(self.cluster_name, self.aws_region)
        now = arrow.utcnow()
        log_file_name = now.format('YYYY-MM-DD')
        self.file_logger = self.logging.get_custom_file_logger(
            params=CustomFileLoggerParams(
                logger_name='cdk-invoker',
                log_dir_name=cluster_logs_dir,
                log_file_name=f'cdk_{log_file_name}.log',
                when='midnight',
                interval=1,
                backupCount=10
            ),
            log_level=logging.INFO,
            fmt='[%(asctime)s] %(message)s'
        )

        cluster_deployments_dir = ideaadministrator.props.cluster_deployments_dir(self.cluster_name, self.aws_region)
        self.deployment_dir = os.path.join(cluster_deployments_dir, self.deployment_id)
        os.makedirs(self.deployment_dir, exist_ok=True)

        self.cluster_config_db = ClusterConfigDB(
            cluster_name=self.cluster_name,
            aws_region=self.aws_region,
            aws_profile=self.aws_profile
        )

        if self.module_id == 'bootstrap':
            self.module_name = 'bootstrap'
        else:
            module_info = self.cluster_config_db.get_module_info(self.module_id)
            self.module_name = module_info['name']

        self.cdk_home = ideaadministrator.props.cluster_cdk_dir(
            cluster_name=self.cluster_name,
            aws_region=self.aws_region
        )

        cdk_json = os.path.join(self.cdk_home, 'cdk.json')
        if not os.path.isfile(cdk_json):
            cdk_json_template = os.path.join(ideaadministrator.props.resources_dir, 'cdk', 'cdk.json')
            shutil.copy(cdk_json_template, cdk_json)

        self.MODULE_MAPPING_INVOKE_MAPPING: Dict[str, ()] = {
            constants.MODULE_SCHEDULER: self.invoke_scheduler,
        }

    def log(self, message: str):
        """
        use this method to log additional information for debugging to file
        do NOT use or update this method to print() to console to keep the console UX as simple and clean as possible.
        :param message:
        """
        self.file_logger.info(f'(DeploymentId: {self.deployment_id}) {message}')

    def log_invocation_context(self):
        self.log(f'[InvocationContext] ClusterName: {self.cluster_name}, '
                 f'Region: {self.aws_region}, '
                 f'Profile: {self.aws_profile}, '
                 f'Rollback: {self.rollback}, '
                 f'ModuleName: {self.module_name}, '
                 f'ModuleId: {self.module_id}')

    def exec_shell(self, shell_cmd: str, silent=False, **_):

        def callback(line):

            line = str(line).rstrip()
            if Utils.is_not_empty(line):
                self.log(message=line)

            if silent:
                return

            print(line, flush=True)

        shell = ShellInvoker(cwd=self.cdk_home)

        env = ideaadministrator.props.get_env()
        # to ensure cdk nodejs lib does not use some other aws profile,
        # override AWS_DEFAULT_PROFILE to the profile given in params
        # this resolves the below installation error:
        # Environment aws://<target-account>/us-east-1 failed bootstrapping: Error: Need to perform AWS calls for account target-account, but the current credentials are for <something-else>
        if Utils.is_not_empty(self.aws_profile):
            env['AWS_DEFAULT_PROFILE'] = self.aws_profile

        env_trace = {}
        for env_key, env_value in env.items():
            # skip sensitive values
            if not env_key.startswith(('IDEA', 'AWS')):
                continue
            env_trace[env_key] = env_value

        self.log(f'Env: {Utils.to_json(env_trace)}')
        self.log(f'shell> {shell_cmd}')

        process = shell.invoke_stream(
            cmd=shell_cmd,
            callback=callback,
            shell=True,
            env=env,
            start_new_session=True
        )

        try:
            return_code = process.start_streaming()
        except KeyboardInterrupt:
            self.log('KeyboardInterrupt')
            process.send_stop_signal()
            return_code = process.wait()

        self.log(f'ExitCode: {return_code}')

        if return_code != 0:
            raise SystemExit(return_code)

    def get_cdk_app_cmd(self) -> str:
        """
        Returns the command to build the CDK app
        when dev_mode is true, invoke automation is used to ensure sources instead of calling idea-admin
        :return:
        """
        cdk_app_args = [
            '--cluster-name',
            self.cluster_name,
            '--aws-region',
            self.aws_region,
            '--module-id',
            self.module_id,
            '--module-name',
            self.module_name,
            '--deployment-id',
            self.deployment_id,
            '--termination-protection',
            str(self.termination_protection).lower()
        ]

        # bug fix for below error
        # Environment aws://<target-account>/us-east-1 failed bootstrapping: Error: Need to perform AWS calls for account target-account, but the current credentials are for <something-else>
        if Utils.is_not_empty(self.aws_profile):
            cdk_app_args += [
                '--aws-profile',
                self.aws_profile
            ]

        if ideaadministrator.props.is_dev_mode():
            args = ['cdk', 'cdk-app'] + cdk_app_args
            args_encoded = Utils.base64_encode(Utils.to_json(args))

            cdk_app_cmd = f'invoke ' \
                          f'--search-root "{ideaadministrator.props.dev_mode_project_root_dir}" ' \
                          f'cli.admin --args {args_encoded}'

            args_trace = ' '.join(args)
            cdk_app_cmd_trace = f'invoke ' \
                                f'--search-root "{ideaadministrator.props.dev_mode_project_root_dir}" ' \
                                f'cli.admin --args base64([{args_trace}])'
            self.log(f'CDKApp (DevMode): {cdk_app_cmd_trace}')
        else:
            cdk_app_args_s = ' '.join(cdk_app_args)
            cdk_app_cmd = f'res-admin cdk cdk-app {cdk_app_args_s}'
            self.log(f'CDKApp: {cdk_app_cmd}')

        return cdk_app_cmd

    def setup_cluster_cdk_dir(self):
        cluster_cdk_dir = ideaadministrator.props.cluster_cdk_dir(
            cluster_name=self.cluster_name,
            aws_region=self.aws_region
        )
        cdk_json = os.path.join(cluster_cdk_dir, 'cdk.json')
        if not os.path.isfile(cdk_json):
            cdk_json_template = os.path.join(ideaadministrator.props.resources_dir, 'cdk', 'cdk.json')
            shutil.copy(cdk_json_template, cdk_json)

    def get_cdk_command(self, name: str, params: Optional[List[str]] = None, context_params: Dict[str, str] = None) -> str:
        """
        build the cdk command. eg:
        $ cdk deploy --app "res-admin cdk-app -c user-config.json [--params] [-c [context_param_key]=[context_param_value]]
        """

        self.setup_cluster_cdk_dir()

        if params is None:
            params = []
        cmd = [ideaadministrator.props.cdk_bin] + name.split(' ') + params
        if name == 'deploy':
            cmd.append(f'--rollback {str(self.rollback).lower()}')
        if Utils.is_not_empty(self.aws_profile):
            cmd.append(f'--profile {self.aws_profile}')
        if context_params is not None:
            for key, value in context_params.items():
                cmd.append(f'-c {key}={value}')
        cmd.append(f'--change-set-name res-{Utils.uuid()}')
        return ' '.join(cmd)

    def cdk_synth(self):
        try:
            self.log('CdkInvoker: Begin Synth')
            self.log_invocation_context()
            cdk_app_cmd = self.get_cdk_app_cmd()
            cdk_cmd = self.get_cdk_command(
                'synth',
                params=[
                    f"--app '{cdk_app_cmd}'"
                ])
            self.exec_shell(cdk_cmd, print_cmd=False)
        finally:
            self.log('CdkInvoker: End Synth')

    def cdk_diff(self):
        try:
            self.log('CdkInvoker: Begin Diff')
            self.log_invocation_context()
            cdk_app_cmd = self.get_cdk_app_cmd()
            cdk_cmd = self.get_cdk_command(
                'diff',
                params=[
                    f"--app '{cdk_app_cmd}'"
                ])
            self.exec_shell(cdk_cmd, print_cmd=False)
        finally:
            self.log('CdkInvoker: End Diff')

    def cdk_destroy(self):
        try:
            self.log('CdkInvoker: Begin Destroy')
            self.log_invocation_context()
            cdk_app_cmd = self.get_cdk_app_cmd()
            cdk_cmd = self.get_cdk_command(
                'destroy',
                params=[
                    f"--app '{cdk_app_cmd}'"
                ])
            self.exec_shell(cdk_cmd, print_cmd=True)
        finally:
            self.log('CdkInvoker: End Destroy')

    def build_and_upload_bootstrap_package(self, bootstrap_context: BootstrapContext,
                                           bootstrap_package_basename: str,
                                           bootstrap_components: List[str],
                                           force_build=False,
                                           upload=True) -> str:
        """
        render the bootstrap package and upload to the cluster's s3 bucket.
        returns the S3 uri of the uploaded bootstrap package
        """

        if ideaadministrator.props.is_dev_mode():
            bootstrap_source_dir = ideaadministrator.props.dev_mode_bootstrap_source_dir
        else:
            bootstrap_source_dir = os.path.join(ideaadministrator.props.resources_dir, 'bootstrap')

        builder = BootstrapPackageBuilder(
            bootstrap_context=bootstrap_context,
            source_directory=bootstrap_source_dir,
            target_package_basename=bootstrap_package_basename,
            components=bootstrap_components,
            tmp_dir=self.deployment_dir,
            force_build=force_build
        )
        bootstrap_package_archive_file = builder.build()
        session = Utils.create_boto_session(self.aws_region, self.aws_profile)
        s3_client = session.client('s3')

        cluster_s3_bucket = bootstrap_context.config.get_string('cluster.cluster_s3_bucket', required=True)
        bootstrap_package_uri = f's3://{cluster_s3_bucket}/idea/bootstrap/{os.path.basename(bootstrap_package_archive_file)}'

        if upload:
            print(f'uploading bootstrap package {bootstrap_package_uri} ...')
            s3_client.upload_file(
                Bucket=cluster_s3_bucket,
                Filename=bootstrap_package_archive_file,
                Key=f'idea/bootstrap/{os.path.basename(bootstrap_package_archive_file)}'
            )
            return bootstrap_package_uri

    def upload_release_package(self, bootstrap_context: BootstrapContext, package_name: str, upload=True) -> str:
        if ideaadministrator.props.is_dev_mode():
            package_dist_dir = ideaadministrator.props.dev_mode_project_dist_dir
        else:
            package_dist_dir = ideaadministrator.props.soca_downloads_dir

        app_package = os.path.join(package_dist_dir, package_name)
        if not Utils.is_file(app_package):
            raise exceptions.general_exception(f'package not found: {app_package}')

        cluster_s3_bucket = bootstrap_context.config.get_string('cluster.cluster_s3_bucket', required=True)
        app_package_uri = f's3://{cluster_s3_bucket}/idea/releases/{package_name}'

        if upload:
            aws_client = AwsClientProvider(options=AWSClientProviderOptions(profile=self.aws_profile, region=self.aws_region))
            print(f'uploading release package: {app_package_uri} ...')
            aws_client.s3().upload_file(
                Bucket=cluster_s3_bucket,
                Filename=app_package,
                Key=f'idea/releases/{os.path.basename(app_package)}'
            )

        return app_package_uri


    def invoke_scheduler(self, **kwargs):
        upload_release_package = Utils.get_value_as_bool('upload_release_package', kwargs, True)
        render_bootstrap_package = Utils.get_value_as_bool('render_bootstrap_package', kwargs, True)
        force_build_bootstrap = Utils.get_value_as_bool('force_build_bootstrap', kwargs, True)
        upload_bootstrap_package = Utils.get_value_as_bool('upload_bootstrap_package', kwargs, True)
        deploy_stack = Utils.get_value_as_bool('deploy_stack', kwargs, True)

        cluster_config = ClusterConfig(
            cluster_name=self.cluster_name,
            aws_region=self.aws_region,
            aws_profile=self.aws_profile,
            module_id=self.module_id,
            module_set=self.module_set
        )

        base_os = cluster_config.get_string('scheduler.base_os', required=True)
        instance_type = cluster_config.get_string('scheduler.instance_type', required=True)
        bootstrap_context = BootstrapContext(
            config=cluster_config,
            module_name=self.module_name,
            module_id=self.module_id,
            module_set=self.module_set,
            base_os=base_os,
            instance_type=instance_type
        )

        app_package_uri = self.upload_release_package(
            bootstrap_context=bootstrap_context,
            package_name=f'idea-scheduler-{ideaadministrator.props.current_release_version}.tar.gz',
            upload=upload_release_package
        )
        bootstrap_context.vars.app_package_uri = app_package_uri

        log_files = [
            CloudWatchAgentLogFileOptions(
                file_path='/opt/idea/app/logs/**.log',
                log_group_name=f'/{self.cluster_name}/{self.module_id}',
                log_stream_name='application_{ip_address}'
            )
        ]
        if cluster_config.get_string('scheduler.provider', required=True) == constants.SCHEDULER_OPENPBS:
            log_files += [
                CloudWatchAgentLogFileOptions(
                    file_path='/var/spool/pbs/server_logs/**.log',
                    log_group_name=f'/{self.cluster_name}/{self.module_id}/openpbs',
                    log_stream_name='server_logs_{ip_address}'
                ),
                CloudWatchAgentLogFileOptions(
                    file_path='/var/spool/pbs/sched_logs/**.log',
                    log_group_name=f'/{self.cluster_name}/{self.module_id}/openpbs',
                    log_stream_name='sched_logs_{ip_address}'
                ),
                CloudWatchAgentLogFileOptions(
                    file_path='/var/spool/pbs/server_priv/accounting/**.log',
                    log_group_name=f'/{self.cluster_name}/{self.module_id}/openpbs',
                    log_stream_name='accounting_logs_{ip_address}'
                )
            ]
        BootstrapUtils.check_and_attach_cloudwatch_logging_and_metrics(
            bootstrap_context=bootstrap_context,
            metrics_namespace=f'{self.cluster_name}/{self.module_id}',
            node_type=constants.NODE_TYPE_APP,
            enable_logging=cluster_config.get_bool('scheduler.cloudwatch_logs.enabled', False),
            log_files=log_files
        )

        bootstrap_package_uri = None
        if render_bootstrap_package or upload_bootstrap_package:
            bootstrap_package_uri = self.build_and_upload_bootstrap_package(
                bootstrap_context=bootstrap_context,
                bootstrap_package_basename=f'bootstrap-{self.module_id}-{self.deployment_id}',
                bootstrap_components=[
                    'scheduler'
                ],
                upload=upload_bootstrap_package,
                force_build=force_build_bootstrap
            )

        if upload_release_package and upload_bootstrap_package and deploy_stack:
            outputs_file = os.path.join(self.deployment_dir, 'scheduler-outputs.json')
            cdk_app_cmd = self.get_cdk_app_cmd()
            cdk_cmd = self.get_cdk_command('deploy', params=[
                f"--app '{cdk_app_cmd}' ",
                f'--outputs-file {outputs_file} ',
                '--require-approval never'
            ], context_params={
                'bootstrap_package_uri': bootstrap_package_uri
            })
            self.exec_shell(cdk_cmd)

    def invoke(self, **kwargs):

        try:
            self.log('CdkInvoker: Begin')
            self.log_invocation_context()

            if self.module_name not in self.MODULE_MAPPING_INVOKE_MAPPING:
                self.log(f'module name not found: {self.module_name}')
                return

            self.MODULE_MAPPING_INVOKE_MAPPING[self.module_name](**kwargs)
        finally:
            self.log('CdkInvoker: End')
