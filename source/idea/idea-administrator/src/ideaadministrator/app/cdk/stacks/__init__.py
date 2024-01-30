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


from .base_stack import IdeaBaseStack
from .bootstrap_stack import SocaBootstrapStack
from .cluster_stack import ClusterStack
from .identity_provider_stack import IdentityProviderStack
from .directoryservice_stack import DirectoryServiceStack
from .shared_storage_stack import SharedStorageStack
from .cluster_manager_stack import ClusterManagerStack
from .scheduler_stack import SchedulerStack
from .bastion_host_stack import BastionHostStack
from .virtual_desktop_controller_stack import VirtualDesktopControllerStack
from .metrics_stack import MetricsStack
