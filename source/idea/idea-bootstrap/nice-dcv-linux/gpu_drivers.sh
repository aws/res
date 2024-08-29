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

# Begin: Install GPU Drivers
set -x

while getopts o:r:n:g:s: opt
do
    case "${opt}" in
        o) BASE_OS=${OPTARG};;
        r) AWS_REGION=${OPTARG};;
        n) RES_ENVIRONMENT_NAME=${OPTARG};;
        g) GPU_FAMILY=${OPTARG};;
        s) SCRIPT_DIR=${OPTARG};;
    esac
done

if [[ -z "$BASE_OS" || -z "$AWS_REGION" || -z "$RES_ENVIRONMENT_NAME" || -z "$GPU_FAMILY" || -z "$SCRIPT_DIR" ]]; then
  echo "One or more of the required parameters is not provided..."
  exit 1
fi

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

function install_nvidia_grid_drivers () {
  which nvidia-smi > /dev/null 2>&1
  if [[ "$?" == "0" ]]; then
    log_info "GPU driver already installed. Skip."
    return 0
  fi

  log_info "Installing NVIDIA GRID Drivers"
  mkdir -p /root/bootstrap/gpu_drivers
  pushd /root/bootstrap/gpu_drivers

  local AWS=$(command -v aws)
  local NVIDIA_S3_BUCKET_URL=$($AWS dynamodb get-item \
                        --region "$AWS_REGION" \
                        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "global-settings.gpu_settings.nvidia.s3_bucket_url"}}' \
                        --output text \
                        | awk '/VALUE/ {print $2}')
  local DRIVER_BUCKET_REGION=$(curl -s --head $NVIDIA_S3_BUCKET_URL | grep bucket-region | awk '{print $2}' | tr -d '\r\n')
  local NVIDIA_S3_BUCKET_PATH=$($AWS dynamodb get-item \
                        --region "$AWS_REGION" \
                        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "global-settings.gpu_settings.nvidia.s3_bucket_path"}}' \
                        --output text \
                        | awk '/VALUE/ {print $2}')
  $AWS --region ${DRIVER_BUCKET_REGION} s3 cp --quiet --recursive $NVIDIA_S3_BUCKET_PATH .
  local x_server_pid=$(cat /tmp/.X0-lock)
  if [[ ! -z "${x_server_pid}" ]]; then
    kill $x_server_pid
  fi

  /bin/sh NVIDIA-Linux-x86_64*.run --no-precompiled-interface --run-nvidia-xconfig --no-questions --accept-license --silent
  log_info "X server configuration for GPU start..."
  # If you are using NVIDIA vGPU software version 14.x or greater on the G4dn, G5, or G5g instances, disable GSP with the following commands.
  touch /etc/modprobe.d/nvidia.conf
  echo "options nvidia NVreg_EnableGpuFirmware=0" | sudo tee --append /etc/modprobe.d/nvidia.conf

  rm -rf /etc/X11/XF86Config*
  local NVIDIAXCONFIG=$(which nvidia-xconfig)
  $NVIDIAXCONFIG --preserve-busid --enable-all-gpus
  log_info "X server configuration for GPU end..."
  set_reboot_required "Installed NVIDIA Grid Driver"
  popd
}

function install_nvidia_public_drivers() {
  which nvidia-smi > /dev/null 2>&1
  if [[ "$?" == "0" ]]; then
    log_info "GPU driver already installed. Skip."
    return 0
  fi

  # Instance	Product Type	Product Series	Product
  # G2	      GRID	        GRID Series	    GRID K520
  # G3/G3s    Tesla	        M-Class	        M60
  # G4dn      Tesla	        T-Series	      T4
  # G5        Tesla	        A-Series	      A10 - G5  (instances require driver version 470.00 or later)
  # G5g       Tesla	        T-Series	      NVIDIA T4G  (G5g instances require driver version 470.82.01 or later. The operating systems is Linux aarch64)
  # P2        Tesla	        K-Series	      K80
  # P3        Tesla	        V-Series	      V100
  # P4d       Tesla	        A-Series	      A100 (320 GB HBM2 GPU memory)
  # P4de      Tesla	        A-Series	      A100 (640 GB HBM2e GPU memory)

  local AWS=$(command -v aws)
  local INSTANCE_FAMILY=$(instance_family)
  local DRIVER_VERSION=$($AWS dynamodb get-item \
                        --region "$AWS_REGION" \
                        --table-name "$RES_ENVIRONMENT_NAME.cluster-settings" \
                        --key '{"key": {"S": "global-settings.gpu_settings.nvidia_public_driver_versions.$INSTANCE_FAMILY"}}' \
                        --output text \
                        | awk '/VALUE/ {print $2}')

  mkdir -p /root/bootstrap/gpu_drivers
  pushd /root/bootstrap/gpu_drivers

  local MACHINE=$(uname -m)
  curl -fSsl -O https://us.download.nvidia.com/tesla/${DRIVER_VERSION}/NVIDIA-Linux-${MACHINE}-${DRIVER_VERSION}.run

  local x_server_pid=$(cat /tmp/.X0-lock)
  if [[ ! -z "${x_server_pid}" ]]; then
    kill $x_server_pid
  fi

  /bin/sh NVIDIA-Linux-${MACHINE}-${DRIVER_VERSION}.run -q -a -n -s
  log_info "X server configuration for GPU start..."
  local NVIDIAXCONFIG=$(which nvidia-xconfig)
  $NVIDIAXCONFIG --preserve-busid --enable-all-gpus
  log_info "X server configuration for GPU end..."
  set_reboot_required "Installed NVIDIA Public Driver"

  popd
}

function install_amd_gpu_drivers() {
  which -a /opt/amdgpu-pro/bin/clinfo
  if [[ "$?" == "0" ]]; then
    log_info "GPU driver already installed. Skip."
    return 0
  fi
  #
  # Instance GPU
  # G4ad     Radeon Pro V520
  #
  if [[ $BASE_OS =~ ^(amzn2)$ ]]; then
    /bin/bash "$SCRIPT_DIR/../nice-dcv-linux/red_hat/amd_gpu_driver.sh" -r $AWS_REGION -n $RES_ENVIRONMENT_NAME
  elif [[ $BASE_OS =~ ^(rhel8|rhel9)$ ]]; then
    log_warning "The latest AMD driver hasn't supported the current Linux version yet"
    exit 0
  elif [[ $BASE_OS =~ ^(ubuntu2204)$ ]]; then
    /bin/bash "$SCRIPT_DIR/../nice-dcv-linux/debian/amd_gpu_driver.sh"
  else
    log_warning "Base OS not supported."
    exit 1
  fi

  set_reboot_required "Installed AMD GPU Driver"

  mkdir -p /etc/X11/
echo """Section \"ServerLayout\"
    Identifier     \"Layout0\"
    Screen          0 \"Screen0\"
    InputDevice     \"Keyboard0\" \"CoreKeyboard\"
    InputDevice     \"Mouse0\" \"CorePointer\"
EndSection
Section \"Files\"
    ModulePath \"/opt/amdgpu/lib64/xorg/modules/drivers\"
    ModulePath \"/opt/amdgpu/lib/xorg/modules\"
    ModulePath \"/opt/amdgpu-pro/lib/xorg/modules/extensions\"
    ModulePath \"/opt/amdgpu-pro/lib64/xorg/modules/extensions\"
    ModulePath \"/usr/lib64/xorg/modules\"
    ModulePath \"/usr/lib/xorg/modules\"
EndSection
Section \"InputDevice\"
    # generated from default
    Identifier     \"Mouse0\"
    Driver         \"mouse\"
    Option         \"Protocol\" \"auto\"
    Option         \"Device\" \"/dev/psaux\"
    Option         \"Emulate3Buttons\" \"no\"
    Option         \"ZAxisMapping\" \"4 5\"
EndSection
Section \"InputDevice\"
    # generated from default
    Identifier     \"Keyboard0\"
    Driver         \"kbd\"
EndSection
Section \"Monitor\"
    Identifier     \"Monitor0\"
    VendorName     \"Unknown\"
    ModelName      \"Unknown\"
EndSection
Section \"Device\"
    Identifier     \"Device0\"
    Driver         \"amdgpu\"
    VendorName     \"AMD\"
    BoardName      \"Radeon MxGPU V520\"
    BusID          \"PCI:0:30:0\"
EndSection
Section \"Extensions\"
    Option         \"DPMS\" \"Disable\"
EndSection
Section \"Screen\"
    Identifier     \"Screen0\"
    Device         \"Device0\"
    Monitor        \"Monitor0\"
    DefaultDepth   24
    Option         \"AllowEmptyInitialConfiguration\" \"True\"
    SubSection \"Display\"
        Virtual    3840 2160
        Depth      32
    EndSubSection
EndSection
"""> /etc/X11/xorg.conf
}

function install_gpu_drivers () {

  # Identify Instance Type and Instance Family and install applicable GPU Drivers
  #
  # Types of Drivers:
  # * Tesla drivers
  #   These drivers are intended primarily for compute workloads, which use GPUs for computational tasks such as parallelized floating-point
  #   calculations for machine learning and fast Fourier transforms for high performance computing applications.
  # * GRID drivers
  #   These drivers are certified to provide optimal performance for professional visualization applications that render content such
  #   as 3D models or high-resolution videos.

  local NODE_TYPE=dcv

  local INSTANCE_TYPE=$(instance_type)
  local INSTANCE_FAMILY=$(instance_family)

  local MACHINE=$(uname -m)
  log_info "Detected GPU instance type: ${INSTANCE_TYPE}. Installing GPU Drivers ..."

  # refer to: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html
  # Available drivers by instance type for Tesla vs Grid mapping.
  # we'll use NODE_TYPE="dcv" to install Grid drivers and NODE_TYPE="compute" to install Tesla drivers.
  case ${INSTANCE_FAMILY} in
    p4d|p4de)
      log_info "Intel / NVIDIA A100"
      # Tesla driver: Yes, GRID driver: No
      install_nvidia_public_drivers
      ;;
    p3)
      log_info "Intel / NVIDIA Tesla V100"
      # Tesla driver: Yes, GRID driver: Yes (Using Marketplace AMIs only)
      if [[ ${NODE_TYPE} == "dcv" ]]; then
        install_nvidia_grid_drivers
      else
        install_nvidia_public_drivers
      fi
      ;;
    p2)
      log_info "Intel / NVIDIA K80"
      # Tesla driver: Yes, GRID driver: No
      install_nvidia_public_drivers
      ;;
    g5)
      log_info "AMD / NVIDIA A10G"
      # Tesla driver: Yes, GRID driver: Yes
      if [[ ${NODE_TYPE} == "dcv" ]]; then
        install_nvidia_grid_drivers
      else
        install_nvidia_public_drivers
      fi
      ;;
    g5g)
      log_info "Arm / NVIDIA T4G"
      # Tesla driver: Yes, GRID driver: No
      # This Tesla driver also supports optimized graphics applications specific to the ARM64 platform
      install_nvidia_public_drivers
      ;;
    g4dn)
      log_info "Intel / NVIDIA T4"
      # Tesla driver: Yes, GRID driver: Yes
      if [[ ${NODE_TYPE} == "dcv" ]]; then
        install_nvidia_grid_drivers
      else
        install_nvidia_public_drivers
      fi
      ;;
    g4ad)
      log_info "AMD / AMD Radeon Pro V520"
      install_amd_gpu_drivers
      ;;
    g3|g3s)
      log_info "Intel / NVIDIA Tesla M60"
      # Tesla driver: Yes, GRID driver: Yes
      if [[ ${NODE_TYPE} == "dcv" ]]; then
        install_nvidia_grid_drivers
      else
        install_nvidia_public_drivers
      fi
      ;;
    g2)
      log_info "Intel / NVIDIA Tesla M60"
      # Tesla driver: Yes, GRID driver: No
      install_nvidia_public_drivers
      ;;
  esac
}

if [[ $GPU_FAMILY =~ ^(NVIDIA|AMD)$ ]]; then
  install_gpu_drivers
else
  log_info "GPU InstanceType not detected. Skip."
fi
# End: Install GPU Drivers
