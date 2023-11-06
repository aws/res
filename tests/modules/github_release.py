'''
This script will prepare your output
'''

import argparse
import sys
import fileinput
import random
import string
import os
from shutil import copy, copytree, rmtree


def update_version(version):
    print("============ Updating SOCA version ============")
    for line in fileinput.input(
        [f"{BUILD_DIRECTORY}installer/default_config.yml",
         f"{BUILD_DIRECTORY}source/soca/cluster_web_ui/templates/common/horizontal_menu_bar.html",
         f"{BUILD_DIRECTORY}source/soca/cluster_web_ui/dcv_cloudformation_builder.py",
         f"{BUILD_DIRECTORY}source/soca/cluster_web_ui/config.py",
         f"{BUILD_DIRECTORY}installer/resources/src/install_soca.py",
         f"{BUILD_DIRECTORY}installer/resources/src/cdk_construct.py",
         f"{BUILD_DIRECTORY}source/soca/cluster_manager/add_nodes.py",
         f"{BUILD_DIRECTORY}source/soca/cluster_manager/configuration.py",
         f"{BUILD_DIRECTORY}source/soca/cluster_manager/dispatcher.py",
         f"{BUILD_DIRECTORY}source/soca/cluster_manager/dcv_alb_manager.py",
         f"{BUILD_DIRECTORY}source/soca/cluster_manager/nodes_manager.py",
         f"{BUILD_DIRECTORY}source/soca/cluster_manager/cloudformation_builder.py",
         f"{BUILD_DIRECTORY}source/soca/cluster_analytics/desktop_hosts_tracking.py",
         f"{BUILD_DIRECTORY}source/soca/cluster_analytics/job_tracking.py",
         ], inplace=True):
        print(line.replace('__VERSION__', version).replace('\n', ''))

    print("Pass")


def remove_unwanted_content():
    print("============ Removing unwanted dirs (dist etc ..) ============")
    content_to_remove = ["source/dist",
                         "installer/dist",
                         "installer/resources/src/envs",
                         "installer/resources/src/cdk.out",
                         "installer/resources/src/cdk.context.json",
                         "installer/resources/src/installer_history.txt"]

    for content in content_to_remove:
        print(f"Removing (if present) {BUILD_DIRECTORY}{content}")
        content_to_check = f"{BUILD_DIRECTORY}{content}"
        try:
            if os.path.isdir(content_to_check) is True:
                rmtree(content_to_check)
            else:
                print(f"{content_to_check} is a file")
                os.remove(content_to_check)

        except FileNotFoundError:
            print("File/Folder does not exist, ignoring ...")

    print("Pass")


def build_github_version():
    print("============ Creating SOCA Structure ============")
    targets = ['docs',
               'source',
               'installer',
               '.gitattributes',
               '.gitignore',
               'CHANGELOG.md',
               'CODE_OF_CONDUCT.md',
               'CONTRIBUTING.md',
               'LICENSE.txt',
               'NOTICE.txt',
               'README.md',
               'THIRD_PARTY_LICENSES.txt',
               'mkdocs.yml',
               '.github']

    # Copy all files to a new build folder
    for target in targets:
        if os.path.isdir(SOCA_DIRECTORY + "/" + target):
            copytree(SOCA_DIRECTORY + "/" + target, BUILD_DIRECTORY + '/' + target)
        else:
            copy(SOCA_DIRECTORY + "/" + target, BUILD_DIRECTORY + '/' + target)
    print("Pass")


def get_input(prompt):
    if sys.version_info[0] >= 3:
        response = input(prompt)
    else:
        # Python 2
        response = raw_input(prompt)
    return response


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', '-v', type=str, required=True, help='The version of SOCA you want to build')
    args = parser.parse_args()

    soca_version = args.version
    unique_id = ''.join(random.choice(string.ascii_lowercase) + random.choice(string.digits) for i in range(2))
    SOCA_DIRECTORY = f"{os.path.dirname(os.path.realpath(__file__))}/../.."
    BUILD_DIRECTORY = f"{SOCA_DIRECTORY}/github/{unique_id}/"
    os.makedirs(BUILD_DIRECTORY)

    build_github_version()
    update_version(soca_version)
    remove_unwanted_content()
    print("==================\n\n\n\n")
    print(f"SOCA {soca_version} ready.\nUpload the content of {BUILD_DIRECTORY} to Github ")
