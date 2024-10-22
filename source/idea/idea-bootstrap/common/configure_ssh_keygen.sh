#!/bin/bash

set -x

usage() {
  echo "Usage: $0 [-o base_os] [-s script_dir] [-u username]"
  exit 1
}

while getopts "o:s:u:" opt; do
  case "${opt}" in
    o) BASE_OS=${OPTARG} ;;
    s) SCRIPT_DIR=${OPTARG} ;;
    u) USERNAME=${OPTARG} ;;
    *) usage ;;
  esac
done

[[ -z "$BASE_OS" || -z "$SCRIPT_DIR" || -z "$USERNAME" ]] && { echo "Missing required parameters..."; exit 1; }

source "$SCRIPT_DIR/../common/bootstrap_common.sh"

setup_pam() {
  local pam_file=$1
  local tmp_file
  tmp_file=$(mktemp)

  # Check if the file already contains the required line
  if grep -q "^session.*ssh_keygen" "$pam_file"; then
    rm "$tmp_file"
    return
  fi

  # Create the new file with the added lines
  awk '
    /^session.*/ && !done {
      print "session\toptional\tpam_mkhomedir.so silent skel=/etc/skel umask=0077\nsession\toptional\tssh_keygen.so"
      done=1
    } 1' "$pam_file" > "$tmp_file"

  # Replace the original file with the updated file
  mv "$tmp_file" "$pam_file"
}

# Configure PAM based on the operating system
case "$BASE_OS" in
  ubuntu2204)
    setup_pam "/etc/pam.d/common-session"
    ;;
  amazonlinux2|rhel7|rhel8|rhel9)
    for file in password-auth system-auth; do
      setup_pam "/etc/pam.d/${file}"
    done
    ;;
  *)
    echo "Unsupported OS: $BASE_OS"
    exit 1
    ;;
esac

# Trigger the PAM module for the specified user
su - "$USERNAME" -c "exit"

echo "PAM module triggered for user $USERNAME"
