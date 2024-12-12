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

import os
from invoke import task, Context
import shutil


@task
def prepare_artifacts(c):
    # type: (Context) -> None
    """
    copy docker artifacts to deployment directory
    """
    release_version = idea.props.idea_release_version
    all_package_archive = os.path.join(idea.props.project_dist_dir, f'all-{release_version}.tar.gz')
    if not os.path.isfile(all_package_archive):
        raise Exception(f'${all_package_archive} not found')

    shutil.copy(all_package_archive, idea.props.deployment_administrator_dir)
    shutil.copy(all_package_archive, idea.props.deployment_ad_sync_dir)


@task
def build_installer_image(c, no_cache=False, platform="linux/amd64"):
    # type: (Context, bool, str) -> None
    """
    build administrator docker image
    """

    prepare_artifacts(c)

    build(c, "idea-administrator", idea.props.deployment_administrator_dir, no_cache, platform)


@task
def build_ad_sync_image(c, no_cache=False, platform="linux/amd64"):
    # type: (Context, bool, str) -> None
    """
    build ad sync docker image
    """

    prepare_artifacts(c)

    build(c, "ad-sync", idea.props.deployment_ad_sync_dir, no_cache, platform)


def build(c, app_name: str, deployment_dir: str, no_cache=False, platform="linux/amd64"):
    release_version = idea.props.idea_release_version
    build_cmd = str(f'docker build '
                    f'--build-arg PUBLIC_ECR_TAG=v{release_version} '
                    f'-t {app_name}:v{release_version} '
                    f'"{deployment_dir}"')
    if no_cache:
        build_cmd = f'{build_cmd} --no-cache'
    if platform:
        build_cmd = f'{build_cmd} --platform {platform}'
    c.run(build_cmd)


def publish(c, ecr_registry, ecr_tag):
    # type: (Context, str, str) -> None
    """
    publish docker image to an ECR repository
    """
    local_image = f'idea-administrator:{ecr_tag}'
    c.run(f'docker tag {local_image} {ecr_registry}/{local_image}')


@task
def print_commands(c):
    # type: (Context) -> None
    """
    print docker push commands for ECR
    """
    pass
