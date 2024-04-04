#!/bin/bash

set -x

while getopts p:o:n:e:c:s: opt;
do
    case "${opt}" in
        p) PROJECT_ID=${OPTARG};;     # Export PROJECT_ID variable with the value of -p option
        o) OWNER_ID=${OPTARG};;       # Export OWNER_ID variable with the value of -o option
        n) PROJECT_NAME=${OPTARG};;   # Export PROJECT_NAME variable with the value of -n option
        e) ENV_NAME=${OPTARG};;       # Export ENV_NAME variable with the value of -e option
        c) ON_VDI_CONFIGURED_COMMANDS=${OPTARG};; # Export ON_VDI_CONFIGURED_COMMANDS variable with the value of -c option
        s) ON_VDI_START_COMMANDS=${OPTARG};; # Export ON_VDI_START_COMMANDS variable with the value of -s option
        ?) echo "Invalid option for export_res_env_variables.sh script: -${opt}."
           exit 1;;
    esac
done

# Check if /etc/launch_script_environment exists
if [ ! -e "/etc/launch_script_environment" ]; then
    # Define the content to be written to /etc/launch_script_environment
    content="
    ## [BEGIN] RES Launch Script Execution Environment - Do Not Delete
    PROJECT_ID=$PROJECT_ID
    OWNER_ID=$OWNER_ID
    PROJECT_NAME=$PROJECT_NAME
    ENV_NAME=$ENV_NAME
    ON_VDI_CONFIGURED_COMMANDS=$ON_VDI_CONFIGURED_COMMANDS
    ON_VDI_START_COMMANDS=$ON_VDI_START_COMMANDS
    ## [END] RES Launch Script Execution Environment
    "

    # Write the content to /etc/launch_script_environment
    echo "$content" > /etc/launch_script_environment
fi
