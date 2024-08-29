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


__all__ = (
    'ModuleMetadata',
    'ModuleMetadataHelper'
)

from ideadatamodel import constants, exceptions, SocaBaseModel

from typing import Dict


class ModuleMetadata(SocaBaseModel):
    name: str
    title: str
    type: str
    deployment_priority: int


MODULE_METADATA = [
    ModuleMetadata(name=constants.MODULE_GLOBAL_SETTINGS, title='Global Settings', type=constants.MODULE_TYPE_CONFIG, deployment_priority=0),
    ModuleMetadata(name=constants.MODULE_BOOTSTRAP, title='Bootstrap', type=constants.MODULE_TYPE_STACK, deployment_priority=1),
    ModuleMetadata(name=constants.MODULE_CLUSTER, title='Cluster', type=constants.MODULE_TYPE_STACK, deployment_priority=2),
    ModuleMetadata(name=constants.MODULE_IDENTITY_PROVIDER, title='Identity Provider', type=constants.MODULE_TYPE_STACK, deployment_priority=3),
    ModuleMetadata(name=constants.MODULE_DIRECTORYSERVICE, title='Directory Service', type=constants.MODULE_TYPE_STACK, deployment_priority=3),
    ModuleMetadata(name=constants.MODULE_SHARED_STORAGE, title='Shared Storage', type=constants.MODULE_TYPE_STACK, deployment_priority=4),
    ModuleMetadata(name=constants.MODULE_CLUSTER_MANAGER, title='Cluster Manager', type=constants.MODULE_TYPE_APP, deployment_priority=5),
    ModuleMetadata(name=constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER, title='eVDI', type=constants.MODULE_TYPE_APP, deployment_priority=6),
    ModuleMetadata(name=constants.MODULE_SCHEDULER, title='Scale-Out Computing', type=constants.MODULE_TYPE_APP, deployment_priority=6),
    ModuleMetadata(name=constants.MODULE_BASTION_HOST, title='Bastion Host', type=constants.MODULE_TYPE_STACK, deployment_priority=7)
]


class ModuleMetadataHelper:

    def __init__(self):
        self.module_meta: Dict[str, ModuleMetadata] = {}
        for module_meta in MODULE_METADATA:
            self.module_meta[module_meta.name] = module_meta

    def get_module_metadata(self, module_name: str) -> ModuleMetadata:
        if module_name not in self.module_meta:
            raise exceptions.general_exception(f'module not found for name: {module_name}')
        return self.module_meta[module_name]

    def get_module_title(self, module_name: str) -> str:
        module_meta = self.get_module_metadata(module_name)
        return module_meta.title

    def get_module_deployment_priority(self, module_name: str) -> int:
        module_meta = self.get_module_metadata(module_name)
        return module_meta.deployment_priority
