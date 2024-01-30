#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

#!/bin/bash
set -e

# Check if jq is installed
if ! command -v jq &> /dev/null
then
    echo "jq could not be found. Please install jq to run this script."
    exit 1
fi

# Check if a file path is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <path_to_json_file> <path_to_cdk_json_context_file>"
    exit 1
fi

FILE_PATH=$1
CDK_JSON_PATH=$2

# Check if the file exists
if [ ! -f "$FILE_PATH" ]; then
    echo "File not found: $FILE_PATH"
    exit 1
fi

if [ ! -f "$CDK_JSON_PATH" ]; then
    echo "File not found: $CDK_JSON_PATH"
    exit 1
fi

# Iterate over the list of accounts in the JSON file
jq -c '.parent_stack.regional_stacks[]' $FILE_PATH | while read regional_stack; do
    # You can process each account here. For now, just printing it.
    account=$(jq -r '.account_id' <<< "$regional_stack")
    region=$(jq -r '.region' <<< "$regional_stack")
    echo "Account: $account"
    echo "Region: $region"
    
    tmp=$(mktemp)
    echo "tmp file: $tmp"
    # update the context file with PortalDomain name for this account
    jq ".context.PortalDomainName = \"\\\"$region.integtest.res.hpc.aws.dev\\\"\"" $CDK_JSON_PATH > "$tmp" && mv "$tmp" $CDK_JSON_PATH
    jq ".context.CustomDomainNameforWebApp = \"\\\"web.$region.integtest.res.hpc.aws.dev\\\"\"" $CDK_JSON_PATH > "$tmp" && mv "$tmp" $CDK_JSON_PATH
    jq ".context.CustomDomainNameforVDI = \"\\\"vdi.$region.integtest.res.hpc.aws.dev\\\"\"" $CDK_JSON_PATH > "$tmp" && mv "$tmp" $CDK_JSON_PATH
    echo "Getting credentials for account $account"
    ada credentials update --once --provider isengard --role Admin --account $account
    export AWS_DEFAULT_REGION=$region
    npx cdk bootstrap
    npx cdk synth
    npx cdk deploy --require-approval never RESBuildPipelineStack --context repository_name=DigitalEngineeringPlatform --context branch_name=develop -c deploy=true -c batteries_included=true
done
