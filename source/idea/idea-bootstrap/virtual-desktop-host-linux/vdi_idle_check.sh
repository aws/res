#!/bin/bash
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

set -x

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

LOG_FOLDER="/opt/idea/app/logs/"
LOG_FILE_NAME="vdi_idle_check.log"
IDLE_CONFIG_FILE="/opt/idea/.idle_config.json"

source /etc/environment

source "${SCRIPT_DIR}/../common/bootstrap_common.sh"
source /etc/environment

# direct logs to log file
mkdir -p ${LOG_FOLDER}
LOG_FILE="${LOG_FOLDER}/${LOG_FILE_NAME}"
exec > >(tee -a ${LOG_FILE}) 2>&1

while getopts "r:n:" opt; do
    case "${opt}" in
        r) AWS_REGION="${OPTARG}";;
        n) RES_ENVIRONMENT_NAME="${OPTARG}";;
        *) echo "Invalid option: -${OPTARG}" >&2; exit 1;;
    esac
done

[[ -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" ]] && { log_error "One or more of the required parameters is not provided..."; exit 1; }

get_cluster_setting() {
    local AWS=$(command -v aws)
    $AWS dynamodb get-item \
        --region "$AWS_REGION" \
        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
        --key "{\"key\": {\"S\": \"$1\"}}" \
        --output text \
        --query 'Item.value.S || Item.value.N'
}

vdi_idle_check() {
    local RES_PYTHON=$(command -v res_python)

    # If no idle config file is found, retrieve settings from cluster settings
    if [[ ! -f "$IDLE_CONFIG_FILE" ]]; then
        log_info "Idle config file not found. Retrieved settings from cluster settings."

        local CPU_UTILIZATION_THRESHOLD=$(get_cluster_setting "vdc.dcv_session.cpu_utilization_threshold")
        local IDLE_TIMEOUT=$(get_cluster_setting "vdc.dcv_session.idle_timeout")
        local TRANSITION_STATE=$(get_cluster_setting "vdc.dcv_session.transition_state")
        local VDI_HELPER_API_URL=$(get_cluster_setting "vdc.vdi_helper_api_gateway_url")

        # Create JSON content including TRANSITION_STATE
        local JSON_CONTENT=$(jq -n \
            --arg cpu "$CPU_UTILIZATION_THRESHOLD" \
            --arg timeout "$IDLE_TIMEOUT" \
            --arg api "$VDI_HELPER_API_URL" \
            --arg state "$TRANSITION_STATE" \
            '{idle_cpu_threshold: $cpu, idle_timeout: $timeout, vdi_helper_api_url: $api, transition_state: $state}')

        # Write JSON content to file
        echo "$JSON_CONTENT" > "$IDLE_CONFIG_FILE"
    else
        log_info "Idle config file found. Retrieved settings from the file."

        local CPU_UTILIZATION_THRESHOLD=$(jq -r '.idle_cpu_threshold' "$IDLE_CONFIG_FILE")
        local IDLE_TIMEOUT=$(jq -r '.idle_timeout' "$IDLE_CONFIG_FILE")
        local VDI_HELPER_API_URL=$(jq -r '.vdi_helper_api_url' "$IDLE_CONFIG_FILE")
        local TRANSITION_STATE=$(jq -r '.transition_state' "$IDLE_CONFIG_FILE")
    fi

    local PARENT_DIR=$(dirname "$SCRIPT_DIR")

    $RES_PYTHON "${PARENT_DIR}/vdi-helper/vdi_auto_stop.py" \
        --aws-region "$AWS_REGION" \
        --api-url "$VDI_HELPER_API_URL" \
        --log-file "$LOG_FILE" \
        --cpu-threshold "$CPU_UTILIZATION_THRESHOLD" \
        --idle-timeout "$IDLE_TIMEOUT" \
        --transition-state "$TRANSITION_STATE" \
        --uptime-minimum 5  # Avoid stopping the instance immediately after booting up
}

vdi_idle_check
