#!/bin/bash

#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -x

SEMAPHORE_DIR="/root/bootstrap/semaphore"
APP_INSTALLED_LOCK="${SEMAPHORE_DIR}/app_installed.lock"

if [ -f ${APP_INSTALLED_LOCK} ]; then
  exit 0
fi

while getopts s:m:c:e:n:o:i:t: opt
do
  case "${opt}" in
    s) SCRIPT_DIR=${OPTARG};;
    c) COMPONENT=${OPTARG};;
    m) MODULE_ID=${OPTARG};;
    e) ENVIRONMENT_NAME=${OPTARG};;
    n) PROJECT_NAME=${OPTARG};;
    o) SESSION_OWNER=${OPTARG};;
    i) SESSION_ID=${OPTARG};;
    t) CUSTOM_BROKER_URL=${OPTARG};;
    ?) echo "Invalid option for install_app.sh script: -${opt}."
      exit 1;;
  esac
done

if [[ -z "$COMPONENT" || -z "$MODULE_ID" || -z "$SCRIPT_DIR" || -z "$ENVIRONMENT_NAME" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source /etc/environment

source "${SCRIPT_DIR}/../common/linux/bootstrap_common.sh"
INSTANCE_REGION=$(get_aws_region)

if [[ "${COMPONENT}" == "virtual-desktop-app" ]]; then
  echo "Exporting Credentials" > /root/bootstrap/install_post_reboot.sh
  request_and_export_aws_credentials $INSTANCE_REGION $CUSTOM_BROKER_URL
  export AWS_DEFAULT_PROFILE="bootstrap_profile"
fi

timestamp=$(date +%s)
exec > ${BOOTSTRAP_DIR}/logs/install_app.log.${timestamp} 2>&1

RES_BASE_OS=$(get_base_os)
if [[ ${RES_BASE_OS} =~ ^(ubuntu2204|ubuntu2404)$ ]]; then
    DEBIAN_FRONTEND=noninteractive LC_ALL="en_US.UTF-8" LC_CTYPE="en_US.UTF-8" LANG="en_US.UTF-8" sed -i -e "s/# $LANG.*/$LANG UTF-8/" /etc/locale.gen && locale-gen "en_US.UTF-8" && dpkg-reconfigure --frontend=noninteractive locales
fi

AWS=$(command -v aws)


# Read app download URI from the ClusterSettings table
APP_PACKAGE_URI_KEY="${COMPONENT}.app_package_uri"
if [[ "${COMPONENT}" == "virtual-desktop-controller" ]]; then
  APP_PACKAGE_URI_KEY="${MODULE_ID}.controller.app_package_uri"
elif [[ "${COMPONENT}" == "dcv-connection-gateway" ]]; then
  APP_PACKAGE_URI_KEY="${MODULE_ID}.dcv_connection_gateway.app_package_uri"
elif [[ "${COMPONENT}" == "dcv-broker" ]]; then
  APP_PACKAGE_URI_KEY="${MODULE_ID}.dcv_broker.app_package_uri"
elif [[ "${COMPONENT}" == "virtual-desktop-app" ]]; then
  APP_PACKAGE_URI_KEY="vdi-app.app_package_uri"
fi

APP_PACKAGE_DOWNLOAD_URI=$($AWS dynamodb get-item \
                        --region "$INSTANCE_REGION" \
                        --table-name "$ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "'$APP_PACKAGE_URI_KEY'"}}' \
                        --output text \
                        | awk '/VALUE/ {print $2}')
if [ $? -ne 0 ]; then
  log_info "No app needs to be installed on this host. Skipping..."
  exit 0
fi

$AWS --region ${INSTANCE_REGION} s3 cp "${APP_PACKAGE_DOWNLOAD_URI}" "${BOOTSTRAP_DIR}/"

APP_DEPLOY_DIR="/opt/idea/app"
PACKAGE_ARCHIVE=$(basename "${APP_PACKAGE_DOWNLOAD_URI}")
PACKAGE_NAME="${PACKAGE_ARCHIVE%.tar.gz*}"
PACKAGE_DIR="${BOOTSTRAP_DIR}/${PACKAGE_NAME}"
mkdir -p ${PACKAGE_DIR}
tar -xvf ${BOOTSTRAP_DIR}/${PACKAGE_ARCHIVE} -C ${PACKAGE_DIR}
idea_pip install -r ${PACKAGE_DIR}/requirements.txt
idea_pip install $(ls ${PACKAGE_DIR}/*-lib.tar.gz)
mkdir -p ${APP_DEPLOY_DIR}/${COMPONENT}
mkdir -p ${APP_DEPLOY_DIR}/logs

# copy webapp if exists
if [[ -d "${APP_DEPLOY_DIR}/${COMPONENT}/webapp" ]]; then
  rm -rf "${APP_DEPLOY_DIR}/${COMPONENT}/webapp"
fi
if [[ -d "${PACKAGE_DIR}/webapp" ]]; then
  cp -r ${PACKAGE_DIR}/webapp ${APP_DEPLOY_DIR}/${COMPONENT}
fi

# copy resources if exist
if [[ -d "${APP_DEPLOY_DIR}/${COMPONENT}/resources" ]]; then
  rm -rf "${APP_DEPLOY_DIR}/${COMPONENT}/resources"
fi
if [[ -d "${PACKAGE_DIR}/resources" ]]; then
  cp -r ${PACKAGE_DIR}/resources ${APP_DEPLOY_DIR}/${COMPONENT}
fi

/bin/bash "${SCRIPT_DIR}/../common/linux/supervisord.sh"

MACHINE=$(uname -m)
INSTANCE_FAMILY=$(instance_family)
ENVIRONMENT="
    environment_name=\"$ENVIRONMENT_NAME\",
    AWS_DEFAULT_REGION=\"$INSTANCE_REGION\",
    AWS_REGION=\"$INSTANCE_REGION\",
    RES_BASE_OS=\"$RES_BASE_OS\",
    MACHINE=\"$MACHINE\",
    INSTANCE_FAMILY=\"$INSTANCE_FAMILY\",
    IDEA_APP_DEPLOY_DIR=\"$APP_DEPLOY_DIR\",
    MACHINE=\"$MACHINE\",
    IDEA_MODULE_ID=\"$MODULE_ID\""
# Add environment variables for VDI
if [[ ! -z "${PROJECT_NAME}" ]]; then
    ENVIRONMENT+=",
    PROJECT_NAME=\"$PROJECT_NAME\""
fi
if [[ ! -z "${SESSION_OWNER}" ]]; then
    ENVIRONMENT+=",
    IDEA_SESSION_OWNER=\"$SESSION_OWNER\""
    ENVIRONMENT+=",
    AWS_DEFAULT_PROFILE=\"bootstrap_profile\""
fi
if [[ ! -z "${SESSION_ID}" ]]; then
    ENVIRONMENT+=",
    IDEA_SESSION_ID=\"$SESSION_ID\""
fi

echo "[program:${COMPONENT}]
environment=${ENVIRONMENT}" > /etc/supervisord.d/${COMPONENT}.ini
echo "command=/opt/idea/python/latest/bin/resserver
process_name=${COMPONENT}
redirect_stderr=true
stdout_logfile = /opt/idea/app/logs/stdout.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
startsecs=30
startretries=3
" >> /etc/supervisord.d/${COMPONENT}.ini

systemctl restart supervisord

echo $(date +%s) > ${APP_INSTALLED_LOCK}
