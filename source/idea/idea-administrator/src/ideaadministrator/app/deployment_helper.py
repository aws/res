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

from ideadatamodel import constants, exceptions
from ideasdk.config.cluster_config_db import ClusterConfigDB
from ideaadministrator.app.cdk.cdk_invoker import CdkInvoker
from ideasdk.utils import Utils, ModuleMetadataHelper

from typing import List
from collections import OrderedDict
import threading
import botocore.exceptions
import time


class DeploymentHelper:

    def __init__(self, cluster_name: str, aws_region: str,
                 termination_protection: bool = True,
                 deployment_id: str = None,
                 upgrade: bool = False,
                 all_modules: bool = False,
                 force_build_bootstrap: bool = False,
                 optimize_deployment: bool = False,
                 module_set: str = constants.DEFAULT_MODULE_SET,
                 module_ids: List[str] = None,
                 aws_profile: str = None,
                 rollback: bool = True):

        self.cluster_name = cluster_name
        self.aws_region = aws_region
        self.termination_protection = termination_protection
        self.upgrade = upgrade
        self.rollback = rollback
        self.all_modules = all_modules
        self.module_set = module_set

        if Utils.is_empty(deployment_id):
            deployment_id = Utils.uuid()
        self.deployment_id = deployment_id

        self.force_build_bootstrap = force_build_bootstrap
        self.optimize_deployment = optimize_deployment
        self.aws_profile = aws_profile

        self.module_metadata_helper = ModuleMetadataHelper()

        self.cluster_config_db = ClusterConfigDB(
            cluster_name=cluster_name,
            aws_region=aws_region,
            aws_profile=aws_profile
        )

        self.cluster_modules = {}
        self.initialize_cluster_modules()

        if self.all_modules:
            self.module_ids = self.cluster_modules.keys()
        else:
            self.module_ids = module_ids

    def initialize_cluster_modules(self):
        modules = self.cluster_config_db.get_cluster_modules()
        for module in modules:
            self.cluster_modules[module['module_id']] = module

    def get_all_module_ids(self) -> List[str]:
        pass

    def deploy_module(self, module_id: str):
        module_info = self.cluster_modules[module_id]
        module_name = module_info['name']
        print(f'deploying module: {module_name}, module id: {module_id}')
        CdkInvoker(
            module_id=module_id,
            cluster_name=self.cluster_name,
            aws_region=self.aws_region,
            aws_profile=self.aws_profile,
            rollback=self.rollback,
            termination_protection=self.termination_protection,
            deployment_id=self.deployment_id,
            module_set=self.module_set
        ).invoke(force_build_bootstrap=self.force_build_bootstrap)

    def get_deployment_order(self) -> List[str]:

        module_deployment_order = []

        for module_id in self.module_ids:
            module_info = self.cluster_modules[module_id]
            if module_info is None:
                continue
            if module_info['type'] == constants.MODULE_TYPE_CONFIG:
                continue
            if module_info['status'] == 'deployed':
                if not self.upgrade:
                    continue

            module_deployment_order.append({
                'module_id': module_id,
                'priority': self.module_metadata_helper.get_module_deployment_priority(module_name=module_info['name'])
            })

        module_deployment_order.sort(key=lambda m: m['priority'])

        return [m['module_id'] for m in module_deployment_order]

    def get_optimized_deployment_order(self) -> List[List[str]]:

        deployment_order = self.get_deployment_order()
        module_deployments = OrderedDict()

        for module_id in deployment_order:
            module_info = self.cluster_modules[module_id]
            if module_info is None:
                continue
            if module_info['type'] == constants.MODULE_TYPE_CONFIG:
                continue
            if module_info['status'] == 'deployed':
                if not self.upgrade:
                    continue

            priority = self.module_metadata_helper.get_module_deployment_priority(module_name=module_info['name'])

            if priority in module_deployments:
                module_deployments[priority].append(module_id)
            else:
                module_deployments[priority] = [module_id]

        result = []
        for module_set in module_deployments.values():
            result.append(module_set)
        return result

    def print_no_op_message(self):
        if self.upgrade:
            # will this ever be the case ?
            print('could not find any modules to upgrade.')
        else:
            if len(self.module_ids) == 1:
                print(f'{self.module_ids[0]} is already deployed. use the --upgrade flag to upgrade or re-deploy the module.')
            else:
                module_s = ', '.join(self.module_ids)
                print(f'[{module_s}] are already deployed. use the --upgrade flag to re-deploy these modules.')

    def invoke(self):
        if self.optimize_deployment and len(self.module_ids) > 1:
            optimized_deployment_order = self.get_optimized_deployment_order()
            if len(optimized_deployment_order) == 0:
                self.print_no_op_message()
                return

            print(f'optimized deployment order: {optimized_deployment_order}')
            for modules in optimized_deployment_order:
                threads = []
                for module_id in modules:
                    thread = threading.Thread(
                        name=f'Thread: {module_id}',
                        target=self.deploy_module,
                        kwargs={'module_id': module_id}
                    )
                    threads.append(thread)
                    thread.start()
                    # process the next entry after 10 seconds.
                    time.sleep(10)

                for thread in threads:
                    thread.join()

                # check for deployment status of previous modules
                # if any of them are not deployed, skip deployment of the next module set
                try:
                    self.initialize_cluster_modules()
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == 'ExpiredTokenException':
                        # deployment can take sometimes more than an hour and
                        # credentials can expire for those generated hourly using STS. re-init ClusterConfigDB and boto session
                        self.cluster_config_db = ClusterConfigDB(
                            cluster_name=self.cluster_name,
                            aws_region=self.aws_region,
                            aws_profile=self.aws_profile
                        )
                        self.initialize_cluster_modules()
                    else:
                        raise e

                for module_id in modules:
                    module_info = self.cluster_modules[module_id]
                    if module_info['status'] != 'deployed':
                        raise exceptions.general_exception(f'deployment failed. could not deploy module: {module_id}')

        else:
            deployment_order = self.get_deployment_order()
            if len(deployment_order) == 0:
                self.print_no_op_message()
                return

            for module_id in deployment_order:
                self.deploy_module(module_id)
