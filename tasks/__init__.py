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
import tasks.idea as idea
from invoke import Collection
import os

idea.utils.update_source_paths([
    idea.props.data_model_src,
    idea.props.sdk_src,
    idea.props.administrator_src,
    idea.props.cluster_manager_src,
    idea.props.virtual_desktop_src,
    idea.props.site_packages,
    idea.props.lambda_functions_src
])

import tasks.clean
import tasks.build
import tasks.package
import tasks.release
import tasks.requirements
import tasks.cli
import tasks.integ_tests
import tasks.tests
import tasks.devtool
import tasks.web_portal
import tasks.docker
import tasks.apispec
import tasks.admin

ns = Collection()
ns.configure({
    'run': {
        'echo': True
    }
})

ns.add_collection(devtool)
ns.add_collection(clean)
ns.add_collection(build)
ns.add_collection(package)
ns.add_collection(release)
ns.add_collection(requirements, name='req')
ns.add_collection(cli)
ns.add_collection(web_portal)
ns.add_collection(docker)
ns.add_collection(apispec)
ns.add_collection(admin)
ns.add_collection(tests)
ns.add_collection(integ_tests)

# local development - unique for individual developer.
# local_dev.py is added to .gitignore and is not checked in.
local_dev = os.path.join(idea.props.project_root_dir, 'tasks', 'local_dev.py')
if os.path.isfile(local_dev):
    import tasks.local_dev

    ns.add_collection(local_dev)
