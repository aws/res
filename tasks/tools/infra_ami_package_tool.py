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
from ideasdk.utils import Jinja2Utils
from invoke import Context
import shutil
import os
import re
import yaml
from typing import List, Dict

class InfraAmiPackageTool:

    def __init__(self, c: Context):
        self.c = c

    @property
    def bash_script_name(self) -> str:
        return 'install.sh'

    @property
    def output_archive_basename(self) -> str:
        return 'res-infra-dependencies'

    @property
    def requirements_file_name(self) -> str:
        return 'requirements.txt'

    @property
    def output_archive_name(self) -> str:
        return f'{self.output_archive_basename}.tar.gz'

    @property
    def output_dir(self) -> str:
        return os.path.join(idea.props.project_dist_dir, self.output_archive_basename)

    @property
    def common_dir(self) -> str:
        return os.path.join(self.output_dir, 'common')

    @property
    def all_depencencies_dir(self) -> str:
        return os.path.join(self.output_dir, 'all_dependencies')

    @property
    def package_names(self) -> List[str]:
        return [
            "idea-cluster-manager",
            "idea-virtual-desktop-controller",
            "idea-sdk"
        ]

    def get_global_settings(self) -> Dict:
        idea.console.print('getting global settings ...')
        env = Jinja2Utils.env_using_file_system_loader(search_path=idea.props.global_settings_dir)
        template = env.get_template('settings.yml')
        global_settings = template.render(enabled_modules=['virtual-desktop-controller'], supported_base_os=['amazonlinux2'])
        return yaml.full_load(global_settings)

    def get_all_requirement_files(self) -> List[str]:
        idea.console.print('getting all requirements file ...')
        requirement_files = []
        for package_name in self.package_names:
            requirements_file = os.path.join(idea.props.requirements_dir, f'{package_name}.txt')
            requirement_files.append(requirements_file)
            if not os.path.isfile(requirements_file):
                raise idea.exceptions.build_failed(f'project requirements file not found: {requirements_file}')
        return requirement_files

    def build_infra_python_requirements(self) -> None:
        idea.console.print('building infra python requirements ...')
        requirement_files = self.get_all_requirement_files()
        packages = dict()
        package_list = []
        for requirement_file in requirement_files:
            with open(requirement_file, 'r') as f:
                for line in f:
                    package = line.strip()
                    if re.match('^\w', package):
                        package_name, package_version = package.split('==')
                        if package_name not in packages:
                            packages[package_name] = package_version
                            package_list.append(package)

        with open(os.path.join(self.all_depencencies_dir, self.requirements_file_name), 'w') as f:
            for package in package_list:
                f.write(package + '\n')

    def copy_common_infra_requirements(self) -> None:
        idea.console.print('copying comming script ...')
        common_bootstrap_dir = os.path.join(idea.props.bootstrap_dir, 'common')
        scripts = os.listdir(common_bootstrap_dir)
        for script in scripts:
            if script.endswith('.sh'):
                shutil.copy(os.path.join(common_bootstrap_dir, script), self.common_dir)

    def archive(self) -> None:
        idea.console.print('creating archive ...')
        shutil.make_archive(self.output_dir, 'gztar', self.output_dir)

    def build_bash_script(self) -> str:
        idea.console.print('building dependency installation bash script ...')
        global_settings = self.get_global_settings()
        bash_content = """#!/bin/bash
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
#

#Set up environment variables
set -ex

RES_BASE_OS=amzn2
BOOTSTRAP_DIR=/root/bootstrap
LOGS_DIR=$BOOTSTRAP_DIR/logs
LOG_FILE=$LOGS_DIR/userdata.log
SCRIPT_DIR=$(pwd)

timestamp=$(date +%s)

#Create required directories
mkdir -p $LOGS_DIR

#Create log file
if [[ -f $LOG_FILE ]]; then
  mv $LOG_FILE "${LOG_FILE}.${timestamp}"
fi

exec > $LOG_FILE 2>&1

cd $BOOTSTRAP_DIR
export PATH=$PATH:/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin:/opt/idea/python/latest/bin
machine=$(uname -m)

###Common installs
#AWS CLI
AWS=$(command -v aws)
if [[ `$AWS --version | awk -F'[/.]' '{print $2}'` != 2 ]]; then
  curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
  which unzip > /dev/null 2>&1
  if [[ "$?" != "0" ]]; then
    yum install -y unzip
  fi
  unzip -q awscliv2.zip
  ./aws/install --bin-dir /bin --update
  rm -rf aws awscliv2.zip
fi

#Amazon linux extras
sudo yum install -y amazon-linux-extras

#AWS SSM Agent: 
"""
        bash_content += f"""
systemctl status amazon-ssm-agent
if [[ "$?" != "0" ]]; then
    yum install -y "{global_settings['package_config']['aws_ssm']['x86_64']}"
fi
"""
        bash_content += """
#Jq
yum install -y jq

#efs utils
yum install -y amazon-efs-utils

#EPEL Repo
/bin/bash "${SCRIPT_DIR}/../common/epel_repo.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"

#System Packages
"""
        linux_packages = global_settings['package_config']['linux_packages']
        all_linux_packages = " ".join(linux_packages['application'] 
                 + linux_packages['system'] 
                 + linux_packages['openldap_client'] 
                 + linux_packages['openldap_server'] 
                 + linux_packages['sssd'] 
                 + linux_packages['putty']
        )
        bash_content += f"""
ALL_PACKAGES=({all_linux_packages})
"""
        bash_content += """
yum install -y ${ALL_PACKAGES[*]}
"""
        bash_content += """
#CloudWatch Agent
yum install -y amazon-cloudwatch-agent

#NFS Utils and dependency items
/bin/bash "${SCRIPT_DIR}/../common/nfs_utils.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"

#jq
/bin/bash "${SCRIPT_DIR}/../common/jq.sh" -o $RES_BASE_OS -s "${SCRIPT_DIR}"
"""
        bash_content += f"""
#Python
PYTHON_VERSION="{global_settings['package_config']['python']['version']}"
PYTHON_URL="{global_settings['package_config']['python']['url']}"
"""
        bash_content += """
PYTHON_TGZ=$(basename ${PYTHON_URL})
function install_python () {
  # - ALIAS_PREFIX: Will generate symlinks for python3 and pip3 for the alias:
  #   eg. if ALIAS_PREFIX == 'idea', idea_python and idea_pip will be available for use.
  # - INSTALL_DIR: the location where python will be installed.
  ALIAS_PREFIX="idea"
  INSTALL_DIR="/opt/idea/python"

  PYTHON3_BIN="${INSTALL_DIR}/latest/bin/python3"
  CURRENT_VERSION="$(${PYTHON3_BIN} --version | awk {'print $NF'})"
  if [[ "${CURRENT_VERSION}" == "${PYTHON_VERSION}" ]]; then
    echo "Python already installed and at correct version."
  else

    echo "Python not detected, installing"

    TIMESTAMP=$(date +%s)
    TMP_DIR="/root/bootstrap/python_installer/${ALIAS_PREFIX}-${TIMESTAMP}"
    mkdir -p "${TMP_DIR}"
    pushd ${TMP_DIR}

    wget ${PYTHON_URL}

    tar xvf ${PYTHON_TGZ}
    pushd "Python-${PYTHON_VERSION}"
    PYTHON_DIR="${INSTALL_DIR}/${PYTHON_VERSION}"
    ./configure LDFLAGS="-L/usr/lib64/openssl" \\
                CPPFLAGS="-I/usr/include/openssl" \\
                -enable-loadable-sqlite-extensions \\
                --prefix="${PYTHON_DIR}"

    NUM_PROCS=`nproc --all`
    MAKE_FLAGS="-j${NUM_PROCS}"
    make ${MAKE_FLAGS}
    make ${MAKE_FLAGS} install

    popd
    popd

    # create symlinks
    PYTHON_LATEST="${INSTALL_DIR}/latest"
    ln -sf "${PYTHON_DIR}" "${PYTHON_LATEST}"
    ln -sf "${PYTHON_LATEST}/bin/python3" "${PYTHON_LATEST}/bin/${ALIAS_PREFIX}_python"
    ln -sf "${PYTHON_LATEST}/bin/pip3" "${PYTHON_LATEST}/bin/${ALIAS_PREFIX}_pip"
    pip_command="${ALIAS_PREFIX}_pip"
"""
        bash_content += f"""
    requirements_path="${{SCRIPT_DIR}}/{self.requirements_file_name}"
"""
        bash_content += """
    export PATH=$PATH:/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin:/opt/idea/python/latest/bin
    $pip_command install -r $requirements_path
  fi
}
install_python
"""
        bash_content += f"""
#DCV
rpm --import {global_settings['package_config']['dcv']['gpg_key']}
"""
        bash_content += f"""
#DCV server
DCV_SERVER_URL="{global_settings['package_config']['dcv']['host']['x86_64']['linux']['al2']['url']}"
DCV_SERVER_SHA256_URL="{global_settings['package_config']['dcv']['host']['x86_64']['linux']['al2']['sha256sum']}"
"""
        bash_content += """
wget $DCV_SERVER_URL
DCV_SERVER_TGZ=$(basename $DCV_SERVER_URL)
urlSha256Sum=$(wget -O - ${DCV_SERVER_SHA256_URL})
if [[ $(sha256sum ${DCV_SERVER_TGZ} | awk '{print $1}') != ${urlSha256Sum} ]];  then
    echo -e "FATAL ERROR: Checksum for DCV Server failed. File may be compromised." > /etc/motd
    exit 1
fi
extractDir=$(echo ${DCV_SERVER_TGZ} |  sed 's/\.tgz$//')
mkdir -p ${extractDir}
tar zxvf ${DCV_SERVER_TGZ} -C ${extractDir} --strip-components 1
pushd ${extractDir}
rpm -ivh nice-dcv-web-viewer-*.${machine}.rpm
popd
rm -rf ${extractDir}
RM_TGZ=$(echo $DCV_SERVER_TGZ | sed 's/\.tgz/*tgz*/')
RM_PAT=$(ls -d $RM_TGZ | egrep -v "tgz$")
rm -rf $RM_PAT || true
"""
        bash_content += f"""
#Gateway
GATEWAY_URL="{global_settings['package_config']['dcv']['connection_gateway']['x86_64']['linux']['al2']['url']}"
GATEWAY_SHA256_URL="{global_settings['package_config']['dcv']['connection_gateway']['x86_64']['linux']['al2']['sha256sum']}"
"""
        bash_content += """
wget $GATEWAY_URL
GATEWAY_FILE_NAME=$(basename $GATEWAY_URL)
urlSha256Sum=$(wget -O - $GATEWAY_SHA256_URL)
if [[ $(sha256sum $GATEWAY_FILE_NAME | awk '{print $1}') != ${urlSha256Sum} ]];  then
    echo -e "FATAL ERROR: Checksum for DCV Connection Gateway failed. File may be compromised." > /etc/motd
    exit 1
fi
yum install -y $GATEWAY_FILE_NAME
RM_RPM=$(echo $GATEWAY_FILE_NAME | sed 's/\.rpm/*rpm*/')
rm -f $RM_RPM || true

#Gateway - netcat
yum install -y nc
"""
        bash_content += f"""
#Broker
BROKER_URL="{global_settings['package_config']['dcv']['broker']['linux']['al2']['url']}"
BROKER_SHA256_URL="{global_settings['package_config']['dcv']['broker']['linux']['al2']['sha256sum']}"
"""
        bash_content += """
wget $BROKER_URL
BROKER_FILE_NAME=$(basename $BROKER_URL)
urlSha256Sum=$(wget -O - ${DCV_SESSION_MANAGER_BROKER_SHA256_URL})
if [[ $(sha256sum ${BROKER_FILE_NAME} | awk '{print $1}') != ${urlSha256Sum} ]];  then
    echo -e "FATAL ERROR: Checksum for DCV Broker failed. File may be compromised." > /etc/motd
    exit 1
fi
yum install -y $BROKER_FILE_NAME
RM_RPM=$(echo $BROKER_FILE_NAME | sed 's/\.rpm/*rpm*/')
rm -f $RM_RPM || true
"""
        return bash_content

    def create_all_dependencies_script(self) -> None:
        bash_content = self.build_bash_script()
        with open(os.path.join(self.all_depencencies_dir, self.bash_script_name), 'w') as f:
            f.write(bash_content)

            
    def package(self):
        idea.console.print_header_block(f'package infra-ami-deps')
        
        shutil.rmtree(self.output_dir, ignore_errors=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.common_dir, exist_ok=True)
        os.makedirs(self.all_depencencies_dir, exist_ok=True)
        
        self.build_infra_python_requirements()
        
        self.copy_common_infra_requirements()
        
        self.create_all_dependencies_script()
        
        self.archive()   
        