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

BOOTSTRAP_DIR="/root/bootstrap"

function exit_fail () {
  echo "Failed: ${1}"
  exit 1
}

function log_info() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S,%3N")] [INFO] ${1}"
}

function log_warning() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S,%3N")] [WARNING] ${1}"
}

function log_error() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S,%3N")] [ERROR] ${1}"
}

function log_debug() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S,%3N")] [DEBUG] ${1}"
}

function set_reboot_required () {
  log_info "Reboot Required: ${1}"
  echo -n "yes" > ${BOOTSTRAP_DIR}/reboot_required.txt
}

function get_reboot_required () {
  if [[ -f ${BOOTSTRAP_DIR}/reboot_required.txt ]]; then
    cat ${BOOTSTRAP_DIR}/reboot_required.txt
  fi
  echo -n "no"
}

function imds_get () {
  local SLASH=''
  local IMDS_HOST="http://169.254.169.254"
  local IMDS_TTL="300"
  # prepend a slash if needed
  if [[ "${1:0:1}" == '/' ]]; then
    SLASH=''
  else
    SLASH='/'
  fi
  local URL="${IMDS_HOST}${SLASH}${1}"

  # Get an Auth token
  local TOKEN=$(curl --silent -X PUT "${IMDS_HOST}/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: ${IMDS_TTL}")

  # Get the requested value and echo it back
  local OUTPUT=$(curl --silent -H "X-aws-ec2-metadata-token: ${TOKEN}" "${URL}")
  echo -n "${OUTPUT}"
}

function instance_type () {
  local INSTANCE_TYPE=$(imds_get /latest/meta-data/instance-type)
  echo -n "${INSTANCE_TYPE}"
}

function instance_family () {
  local INSTANCE_FAMILY=$(imds_get /latest/meta-data/instance-type | cut -d. -f1)
  echo -n "${INSTANCE_FAMILY}"
}

function instance_id () {
  local INSTANCE_ID=$(imds_get /latest/meta-data/instance-id)
  echo -n "${INSTANCE_ID}"
}

function instance_region () {
  local INSTANCE_REGION=$(imds_get /latest/meta-data/placement/region)
  echo -n "${INSTANCE_REGION}"
}

function get_secret() {
    local SECRET_ID="${1}"
    local MAX_ATTEMPT=10
    local CURRENT_ATTEMPT=0
    local SLEEP_INTERVAL=180
    local AWS=$(which aws)
    local command="${AWS} secretsmanager get-secret-value --secret-id ${SECRET_ID} --query SecretString --region ${AWS_DEFAULT_REGION} --output text"
    while ! secret=$($command); do
        ((CURRENT_ATTEMPT=CURRENT_ATTEMPT+1))
        if [[ ${CURRENT_ATTEMPT} -ge ${MAX_ATTEMPT} ]]; then
            echo "error: Timed out waiting for secret from secrets manager"
            return 1
        fi
        echo "Secret Manager is not ready yet ... Waiting ${SLEEP_INTERVAL} s... Loop count is: ${CURRENT_ATTEMPT}/${MAX_ATTEMPT}"
        sleep ${SLEEP_INTERVAL}
    done
    echo -n "${secret}"
}

function get_server_ip() {
  # Get server IP - based on CR-69639334 - @jasackle
  # This may return multiple IP addresses
  # So we store an array (SERVER_IP_ARRAY) for them and set the SERVER_IP to the first encountered IPv4 address
  # for any future needs in the script for the canonical IPv4 host IP
  local SERVER_IP_ARRAY=($(hostname -I))
  local SERVER_IP=""
  for ip in ${!SERVER_IP_ARRAY[@]}; do
      # Only consider IPv4 as SERVER_IP for now due to PBS interactions with IPv6 addresses.
      # We don't have to worry about the regex false matching on an IPv6 address
      # with an embedded IPv4 address since this is not user input validation.
      # This is just validation from the hostname command outputs.
      # Example 2001:db8::10.0.0.1 becomes 2001:db::a00:1 in-kernel and from hostname command output
      IPV4_COUNT=$(echo ${SERVER_IP_ARRAY[$ip]} | grep -Ec "(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)")
      if [[ -z "${SERVER_IP}" && "${IPV4_COUNT}" -eq '1' ]]; then
          SERVER_IP=${SERVER_IP_ARRAY[$ip]}
      fi
  done
  echo "${SERVER_IP}"
}

# Generate a Shake256 value from the input
function get_shake256() {
  local STR="${1}"
  local SHAKE_LEN="${2}"
  local IDEA_PYTHON=$(command -v idea_python)
  local SHAKE_VAL=$(${IDEA_PYTHON} -c "import sys; import hashlib; print(hashlib.shake_256(''.join(sys.argv[1]).encode('utf-8')).hexdigest(int(sys.argv[2])))" "${STR}" "${SHAKE_LEN}")
  echo -n "${SHAKE_VAL}"
}

function get_shake256_hostname() {
  local HOSTNAME=$(hostname -s)
  local HOSTNAME_PREFIX="IDEA-"
  # This is the overall max len in chars. Generally this will be 15
  # for NetBIOS legacy reasons
  local MAX_LENGTH=15
  # /2 as get_shake256 takes number of hex bytes - which are 2 ASCII char to display
  local ALLOWED_LEN_BYTES=$(((${MAX_LENGTH} - ${#HOSTNAME_PREFIX})/2))
  SHAKE_HOSTNAME=$(get_shake256 "${HOSTNAME}" "${ALLOWED_LEN_BYTES}")
  echo -n "${HOSTNAME_PREFIX}${SHAKE_HOSTNAME}"
}

# fsx for lustre
function add_fsx_lustre_to_fstab () {
  local FS_DOMAIN="${1}"
  local MOUNT_DIR="${2}"
  local MOUNT_OPTIONS=${3}
  local FS_MOUNT_NAME="${4}"

  if [[ -z "${MOUNT_OPTIONS}" ]]; then
    MOUNT_OPTIONS="lustre defaults,noatime,flock,_netdev 0 0"
  fi

  grep -q " ${MOUNT_DIR}/" /etc/fstab
  if [[ "$?" == "0" ]]; then
    log_info "skip add_fsx_lustre_to_fstab: existing entry found for mount dir: ${MOUNT_DIR}"
    return 0
  fi

  # handle cases for scratch file systems during SOCA job submission
  if [[ -z "${FS_MOUNT_NAME}" ]]; then
    local FSX_ID=$(echo "${FS_DOMAIN}" | cut -d. -f1)
    local AWS=$(command -v aws)
    FS_MOUNT_NAME=$($AWS fsx describe-file-systems \
                              --file-system-ids ${FSX_ID}  \
                              --query FileSystems[].LustreConfiguration.MountName \
                              --region ${AWS_DEFAULT_REGION} \
                              --output text)
  fi
  echo "${FS_DOMAIN}@tcp:/${FS_MOUNT_NAME} ${MOUNT_DIR}/ ${MOUNT_OPTIONS}" >> /etc/fstab
}

function remove_fsx_lustre_from_fstab () {
  local MOUNT_DIR="${1}"
  sed -i.bak "\@ ${MOUNT_DIR}/@d" /etc/fstab
}

# efs
function add_efs_to_fstab () {
  local FS_DOMAIN="${1}"
  local MOUNT_DIR="${2}"
  local MOUNT_OPTIONS=${3}

  # Fallback to NFS options for EFS
  if [[ -z "${MOUNT_OPTIONS}" ]]; then
    log_info "# INFO - Using Fallback NFS options for EFS due to no mount_options"
    MOUNT_OPTIONS="nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0"
  fi

  grep -q " ${MOUNT_DIR}/" /etc/fstab
  if [[ "$?" == "0" ]]; then
    log_info "skip add_efs_to_fstab: existing entry found for mount dir: ${MOUNT_DIR}"
    return 0
  fi

  echo "${FS_DOMAIN}:/ ${MOUNT_DIR}/ ${MOUNT_OPTIONS}" >> /etc/fstab
}

function remove_efs_from_fstab () {
  local MOUNT_DIR="${1}"
  sed -i.bak "\@ ${MOUNT_DIR}/@d" /etc/fstab
}

# openzfs
function add_fsx_openzfs_to_fstab () {
  local FS_DOMAIN="${1}"
  local MOUNT_DIR="${2}"
  local MOUNT_OPTIONS=${3}
  local FS_VOLUME_PATH="${4}"

  if [[ -z "${MOUNT_OPTIONS}" ]]; then
    MOUNT_OPTIONS="nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0"
  fi

  grep -q " ${MOUNT_DIR}/" /etc/fstab
  if [[ "$?" == "0" ]]; then
    log_info "skip add_openzfs_to_fstab: existing entry found for mount dir: ${MOUNT_DIR}"
    return 0
  fi

  # eg. filesystem-dns-name:volume-path /localpath nfs nfsver=version defaults 0 0
  echo "${FS_DOMAIN}:${FS_VOLUME_PATH} ${MOUNT_DIR}/ ${MOUNT_OPTIONS}" >> /etc/fstab
}

function remove_fsx_openzfs_from_fstab () {
  local MOUNT_DIR="${1}"
  sed -i.bak "\@ ${MOUNT_DIR}/@d" /etc/fstab
}

# netapp ontap
function add_fsx_netapp_ontap_to_fstab () {
  local FS_DOMAIN="${1}"
  local MOUNT_DIR="${2}"
  local MOUNT_OPTIONS=${3}
  local FS_VOLUME_PATH="${4}"

  if [[ -z "${MOUNT_OPTIONS}" ]]; then
    MOUNT_OPTIONS="nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport 0 0"
  fi

  grep -q " ${MOUNT_DIR}/" /etc/fstab
  if [[ "$?" == "0" ]]; then
    log_info "skip add_netapp_ontap_to_fstab: existing entry found for mount dir: ${MOUNT_DIR}"
    return 0
  fi

  # eg. svm-dns-name:volume-junction-path /fsx nfs nfsvers=version,defaults 0 0
  echo "${FS_DOMAIN}:${FS_VOLUME_PATH} ${MOUNT_DIR}/ ${MOUNT_OPTIONS}" >> /etc/fstab
}

add_s3_bucket() {
    # Check if all required arguments are provided
    if [ "$#" -lt 5 ]; then
        echo "Usage: add_s3_bucket CUSTOM_CREDENTIAL_BROKER_SCRIPT_LOCATION API_URL FS_NAME MOUNT_DIR BUCKET_NAME [READ_ONLY] [PREFIX]"
        return 1
    fi

    # Assign arguments to variables
    local CUSTOM_CREDENTIAL_BROKER_SCRIPT_LOCATION="$1"
    local API_URL="$2"
    local FS_NAME="$3"
    local MOUNT_DIR="$4"
    local BUCKET_NAME="$5"
    local READ_ONLY="${6:-True}"  # Default value for READ_ONLY is "True"
    local PREFIX="${7}"

    # Check if required variables are set
    if [ -z "$CUSTOM_CREDENTIAL_BROKER_SCRIPT_LOCATION" ] || [ -z "$API_URL" ] || [ -z "$FS_NAME" ] || [ -z "$MOUNT_DIR" ] || [ -z "$BUCKET_NAME" ]; then
        echo "Error: Required arguments are not provided."
        return 1
    fi

    # Define additional variables
    local PROFILE_NAME="${FS_NAME}-profile"
    local MOUNT_S3=$(command -v mount-s3)
    local RES_PYTHON=$(command -v res_python)

    # Configure AWS CLI
    aws configure set output json
    aws configure set region ${AWS_DEFAULT_REGION}
    aws configure set credential_process "${RES_PYTHON} ${CUSTOM_CREDENTIAL_BROKER_SCRIPT_LOCATION} --filesystem-name ${FS_NAME} --api-url ${API_URL}" --profile "${PROFILE_NAME}"
    aws configure set output json --profile "${PROFILE_NAME}"
    aws configure set region ${AWS_DEFAULT_REGION} --profile "${PROFILE_NAME}"

    # Construct mount command
    local mount_command="${MOUNT_S3} ${BUCKET_NAME} ${MOUNT_DIR} --allow-other"

    if [[ "${READ_ONLY}" == "True" ]]; then
      mount_command+=" --read-only"
    elif [[ "${READ_ONLY}" == "False" ]]; then
      mount_command+=" --allow-delete --allow-overwrite --dir-mode 0777 --file-mode 0777"
    fi

    [[ -n "$PREFIX" ]] && mount_command+=" --prefix $PREFIX"  # Add prefix if provided

    # Execute Mount Command
    log_info "Executing mount command: ${mount_command}"
    AWS_PROFILE="${PROFILE_NAME}" ${mount_command}

    local service_name="${FS_NAME}-mount-s3"
    local service_file="/etc/systemd/system/${service_name}.service"
    # Create a systemd service unit file
    tee "${service_file}" > /dev/null << EOF
[Unit]
Description=Mountpoint for Amazon S3 mount
Wants=network.target
AssertPathIsDirectory=${MOUNT_DIR}

[Service]
Type=forking
User=root
ExecStart=/bin/bash -c 'AWS_PROFILE=${PROFILE_NAME} ${mount_command}'
ExecStop=/usr/bin/fusermount -u ${MOUNT_DIR}
Restart=always

[Install]
WantedBy=remote-fs.target
EOF

    # Reload systemd to read the new unit file
    systemctl daemon-reload

    # Enable the service to run at boot
    systemctl enable "${service_name}.service"
}

function remove_fsx_netapp_ontap_from_fstab () {
  local MOUNT_DIR="${1}"
  sed -i.bak "\@ ${MOUNT_DIR}/@d" /etc/fstab
}

function create_jq_ddb_filter () {
  echo '
def convert_from_dynamodb_object:
    def get_property($key): select(keys == [$key])[$key];
       ((objects | { value: get_property("S") })
    // (objects | { value: get_property("N") | tonumber })
    // (objects | { value: get_property("B") })
    // (objects | { value: get_property("M") | map_values(convert_from_dynamodb_object) })
    // (objects | { value: get_property("L") | map(convert_from_dynamodb_object) })
    // (objects | { value: get_property("SS") })
    // (objects | { value: get_property("NS") | map(tonumber) })
    // (objects | { value: get_property("BOOL") })
    // (objects | { value: get_property("BS") })
    // (objects | { value: map_values(convert_from_dynamodb_object) })
    // (arrays | { value: map(convert_from_dynamodb_object) })
    // { value: . }).value
    ;
convert_from_dynamodb_object
' > /root/.convert_from_dynamodb_object.jq
}
