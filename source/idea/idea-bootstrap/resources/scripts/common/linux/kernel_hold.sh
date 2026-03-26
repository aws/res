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

# Kernel version hold management functions
# This script provides functions to lock/unlock kernel versions to prevent unwanted upgrades
# while still allowing installation of packages for the current kernel version
#

source "${SCRIPT_DIR}/bootstrap_common.sh"

function enable_kernel_hold() {
  local BASE_OS="${1}"
  if [[ -z "$BASE_OS" ]]; then
    BASE_OS=$(get_base_os)
  fi
  local CURRENT_KERNEL=$(uname -r)
  log_info "Enabling strict kernel version hold for OS: $BASE_OS, current kernel: $CURRENT_KERNEL"

  case $BASE_OS in
    rhel8|rhel9|rocky9)      
      # Install versionlock plugin if not present
      if ! rpm -q python3-dnf-plugin-versionlock &>/dev/null; then
        log_info "Installing dnf versionlock plugin"
        dnf install -y python3-dnf-plugin-versionlock 2>/dev/null || yum install -y yum-plugin-versionlock 2>/dev/null || true
      fi
      
      # Clear any existing versionlocks
      dnf versionlock clear 2>/dev/null || yum versionlock clear 2>/dev/null || true
      
      # Get list of installed kernel packages and lock them to current version
      local INSTALLED_PACKAGES=$(rpm -qa | grep "^kernel" | grep "${CURRENT_KERNEL}")
      
      for pkg in $INSTALLED_PACKAGES; do
        log_info "Locking package: ${pkg}"
        dnf versionlock add "${pkg}" 2>/dev/null || yum versionlock add "${pkg}" 2>/dev/null || true
      done
      
      log_info "Kernel packages locked to version ${CURRENT_KERNEL}"
      ;;
    *)
      log_warning "Unsupported OS for kernel version hold: $BASE_OS"
      ;;
  esac

  log_info "Strict kernel version hold enabled successfully for $CURRENT_KERNEL"
}

function disable_kernel_hold() {
  local BASE_OS="${1}"
  if [[ -z "$BASE_OS" ]]; then
    BASE_OS=$(get_base_os)
  fi
  log_info "Disabling kernel version hold for OS: $BASE_OS"

  case $BASE_OS in
    rhel8|rhel9|rocky9)
      # Clear versionlocks
      log_info "Clearing versionlocks"
      dnf versionlock clear 2>/dev/null || yum versionlock clear 2>/dev/null || true
      log_info "Removed kernel version hold"
      ;;
    *)
      log_warning "Unsupported OS for kernel hold removal: $BASE_OS"
      ;;
  esac

  log_info "Kernel version hold disabled successfully"
}
