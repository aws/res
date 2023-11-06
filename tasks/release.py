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
from invoke import task, Context

from ideasdk.utils import Utils

import os
import shutil
from typing import List
from pathlib import Path


@task()
def update_version(c, version):
    # type: (Context, str) -> None
    """
    update idea release version in all applicable places
    """
    old_version = idea.props.idea_release_version
    if version is not None and len(version.strip()) > 0:
        print(f'updating RES_VERSION.txt with version: {version}')
        with open(os.path.join(idea.props.project_root_dir, 'RES_VERSION.txt'), 'w') as f:
            f.write(version)

        print(f'updating res-admin.sh with version: {version}')
        idea_admin_sh = os.path.join(idea.props.project_root_dir, 'res-admin.sh')
        with open(idea_admin_sh, 'r') as f:
            content = f.read()
            replace_old = f'IDEA_REVISION=${{IDEA_REVISION:-"v{old_version}"}}'
            replace_new = f'IDEA_REVISION=${{IDEA_REVISION:-"v{version}"}}'
            content = content.replace(replace_old, replace_new)
        with open(idea_admin_sh, 'w') as f:
            f.write(content)

        print(f'updating res_admin-windows.ps1 with version: {version}')
        idea_admin_ps1 = os.path.join(idea.props.project_root_dir, 'res-admin-windows.ps1')
        with open(idea_admin_ps1, 'r') as f:
            content = f.read()
            replace_old = f'$IDEARevision = if ($Env:IDEA_REVISION) {{$Env:IDEA_REVISION}} else {{"v{old_version}"}}'
            replace_new = f'$IDEARevision = if ($Env:IDEA_REVISION) {{$Env:IDEA_REVISION}} else {{"v{version}"}}'
            content = content.replace(replace_old, replace_new)
        with open(idea_admin_ps1, 'w') as f:
            f.write(content)


@task()
def build_opensource_dist(c):
    # type: (Context) -> None
    """
    build open source package for Github
    """

    idea.console.print_header_block('Building OpenSource package for Github ...')

    # callback function to ignore all runtime dependencies that generated automatically during build process
    # passed to shutil.copytree()
    def ignore_callback(src: str, names: List[str]) -> List[str]:
        ignored_names = []
        src_base_name = os.path.basename(src)
        for name in names:
            if name.endswith('.egg-info'):
                ignored_names.append(name)
            if name.startswith('.pytest_cache'):
                ignored_names.append(name)
            if src_base_name == 'webapp' and name == 'build':
                ignored_names.append(name)
            if src_base_name == 'idea-administrator' and name.endswith('tar.gz'):
                ignored_names.append(name)
            if src_base_name == 'deployment' and name in ('idea', 'open-source', 'global-s3-assets'):
                ignored_names.append(name)
            if name in (
                'dist',
                'node_modules',
                '__pycache__',
                '.DS_Store',
                'yarn-error.log',
                'local_dev.py'
            ):
                ignored_names.append(name)

        return ignored_names

    # opensource build dir: build/open-source
    opensource_build_dir = os.path.join(idea.props.project_build_dir, 'open-source')
    if os.path.isdir(opensource_build_dir):
        shutil.rmtree(opensource_build_dir)

    # opensource build source dir: build/open-source/idea
    opensource_build_sources_dir = os.path.join(opensource_build_dir, 'idea')
    os.makedirs(opensource_build_sources_dir)

    # copy all source artifacts to build/open-source
    targets = [
        'deployment',
        'tasks',
        'source',
        'requirements',
        '.github',
        '.editorconfig',
        '.gitattributes',
        '.gitignore',
        'CHANGELOG.md',
        'CODE_OF_CONDUCT.md',
        'CONTRIBUTING.md',
        'LICENSE.txt',
        'NOTICE.txt',
        'README.md',
        'THIRD_PARTY_LICENSES.txt',
        'RES_VERSION.txt',
        'software_versions.yml',
        'res-admin.sh',
        'res-admin-windows.ps1'
    ]
    for target in targets:
        if os.path.isdir(os.path.join(idea.props.project_root_dir, target)):
            shutil.copytree(
                src=os.path.join(idea.props.project_root_dir, target),
                dst=os.path.join(opensource_build_sources_dir, target),
                ignore=ignore_callback
            )
        else:
            shutil.copy(os.path.join(idea.props.project_root_dir, target), os.path.join(opensource_build_sources_dir, target))

    for line in Utils.print_directory_tree(Path(opensource_build_sources_dir)):
        print(line)

    shutil.make_archive(opensource_build_sources_dir, 'zip', opensource_build_sources_dir)
    zip_file = f'{opensource_build_sources_dir}.zip'

    # delete open-source target directory if exists
    opensource_target_dir = os.path.join(idea.props.project_deployment_dir, 'open-source')
    if os.path.isdir(opensource_target_dir):
        shutil.rmtree(opensource_target_dir)
    os.makedirs(opensource_target_dir)

    # copy open-source idea.zip archive to open-source target dir
    target_zip_file = os.path.join(opensource_target_dir, 'idea.zip')
    shutil.copy(zip_file, target_zip_file)

    idea.console.print_header_block(f'OpenSource zip file for Github: {target_zip_file}')


@task()
def build_s3_dist(c, public_ecr, version):
    # type: (Context, str, str) -> None
    """
    build s3 distribution package for global assets
    """
    idea.console.print_header_block('Building S3 distribution package for solution\'s global assets ...')

    # initialize deployment/global-s3-assets directory (delete if exists)
    # global-s3-assets os added to .gitignore
    global_s3_assets_dir = os.path.join(idea.props.project_deployment_dir, 'global-s3-assets')
    if os.path.isdir(global_s3_assets_dir):
        shutil.rmtree(global_s3_assets_dir)
    os.makedirs(global_s3_assets_dir)

    # initialize deployment/regional-s3-assets directory (delete if exists)
    # regional-s3-assets os added to .gitignore
    regional_s3_assets_dir = os.path.join(idea.props.project_deployment_dir, 'regional-s3-assets')
    if os.path.isdir(regional_s3_assets_dir):
        shutil.rmtree(regional_s3_assets_dir)
    os.makedirs(regional_s3_assets_dir)

    # copy cfn template
    cfn_template = 'integrated-digital-engineering-on-aws.template'
    cfn_template_file = os.path.join(idea.props.project_deployment_dir, cfn_template)
    global_cfn_template = os.path.join(global_s3_assets_dir, cfn_template)
    regional_noop_file = os.path.join(regional_s3_assets_dir, 'NoOp')
    shutil.copy(cfn_template_file, global_cfn_template)
    Path(regional_noop_file).touch()  # needed to bypass pipeline requirement of regional assets

    # update template placeholders for ECR repo and image tag
    with open(global_cfn_template, 'r') as f:
        content = f.read()
        replace_old_version = 'IDEA_REVISION="VERSION"'
        replace_new_version = f'IDEA_REVISION="{version}"'
        replace_old_ecr = 'IDEA_ECR_REPO="SOLUTIONS_ECR_REPO/idea-administrator"'
        replace_new_ecr = f'IDEA_ECR_REPO="{public_ecr}/idea-administrator"'
        content = content.replace(replace_old_ecr, replace_new_ecr)
        content = content.replace(replace_old_version, replace_new_version)
    with open(global_cfn_template, 'w') as f:
        f.write(content)

    # convert policy yaml files to json for each partition and copy to:
    # deployment/global-s3-assets/installer_policies/<partition>/<policy-name>.json
    supported_aws_partitions = [
        'aws'
    ]

    policy_source_dir = os.path.join(idea.props.administrator_project_dir, 'resources', 'installer_policies')
    policy_target_dir = os.path.join(global_s3_assets_dir, 'installer_policies')
    os.makedirs(policy_target_dir)

    policy_files = os.listdir(policy_source_dir)

    for aws_partition in supported_aws_partitions:

        partition_target_dir = os.path.join(policy_target_dir, aws_partition)
        os.makedirs(partition_target_dir)

        for policy_file_name in policy_files:
            yaml_file = os.path.join(policy_source_dir, policy_file_name)

            with open(yaml_file, 'r') as f:
                content = f.read()
                content.replace('arn:aws:', f'arn:{aws_partition}:')
                policy_dict = Utils.from_yaml(content)

            json_file = os.path.join(partition_target_dir, policy_file_name.replace('.yml', '.json'))
            with open(json_file, 'w') as f:
                f.write(Utils.to_json(policy_dict, indent=True))

    for line in Utils.print_directory_tree(Path(global_s3_assets_dir)):
        print(line)

    idea.console.print_header_block(f'S3 distribution created successfully: {global_s3_assets_dir}')
