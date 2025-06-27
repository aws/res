#!/bin/bash

set -x

# Path where launch scripts will be downloaded
launch_scripts_path="./launch/scripts"
mkdir -p "$launch_scripts_path"

download_file() {
    local uri=$1
    local destination

    destination=$(basename "${uri#*://}")

    if [[ $uri == s3://* ]]; then
        # Check if AWS CLI is installed
        if ! command -v aws &>/dev/null; then
            echo "AWS CLI is not installed. Please install and configure AWS CLI."
            exit 1
        fi
        aws s3 cp "$uri" "$launch_scripts_path/$destination"
    elif [[ $uri == https://* ]]; then
        # Check if curl is installed
        if ! command -v curl &>/dev/null; then
            echo "curl is not installed. Please install curl to download files from HTTPS URLs."
            exit 1
        fi
        curl -o "$launch_scripts_path/$destination" "$uri"
    elif [[ $uri == file://* ]]; then
        local file_path=${uri#file://}
        cp "$file_path" "$launch_scripts_path/$destination"
    else
        echo "Unsupported URI format: $uri"
        exit 1
    fi

    # Make the downloaded script executable
    chmod +x "$launch_scripts_path/$destination"

    # Get arguments
    shift
    local arguments="$@"

    # Execute the downloaded script with arguments
    "$launch_scripts_path/$destination" $arguments

    # Remove the downloaded script
    rm -f "$destination"
}

download_file "$@"
