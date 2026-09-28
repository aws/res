#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -e
set -o pipefail

# Function to get all image pipeline ARNs from the PrebakedRESReadyAMIsStack
get_pipeline_arns() {
    local stack_name="$1"
    echo "Getting pipeline ARNs from stack: $stack_name" >&2

    # Get all ImagePipeline resources from the nested stack
    local pipeline_arns
    if ! pipeline_arns=$(aws cloudformation describe-stack-resources \
        --stack-name "$stack_name" \
        --query 'StackResources[?ResourceType==`AWS::ImageBuilder::ImagePipeline`].PhysicalResourceId' \
        --output text 2>&1); then
        echo "ERROR: Failed to get pipeline ARNs from stack $stack_name" >&2
        echo "AWS CLI Error: $pipeline_arns" >&2
        return 1
    fi

    echo "$pipeline_arns" | tr '\t' '\n'
}

# Function to trigger an image pipeline
trigger_pipeline() {
    local pipeline_arn="$1"
    echo "Triggering pipeline: $pipeline_arn" >&2

    # Start the image pipeline execution
    local execution_arn
    if ! execution_arn=$(aws imagebuilder start-image-pipeline-execution \
        --image-pipeline-arn "$pipeline_arn" \
        --query 'imageBuildVersionArn' \
        --output text 2>&1); then
        echo "ERROR: Failed to trigger pipeline $pipeline_arn" >&2
        echo "AWS CLI Error: $execution_arn" >&2
        return 1
    fi

    if [ -z "$execution_arn" ] || [ "$execution_arn" = "None" ]; then
        echo "ERROR: Pipeline trigger returned empty execution ARN for $pipeline_arn" >&2
        return 1
    fi

    echo "Started execution: $execution_arn" >&2
    echo "$execution_arn"
}

# Function to check pipeline execution status
check_execution_status() {
    local execution_arn="$1"

    # First check if the execution ARN is valid and the image exists
    if [ -z "$execution_arn" ] || [ "$execution_arn" = "None" ]; then
        echo "PENDING"
        return
    fi

    # Try to get the image build version status with better error handling
    local status
    status=$(aws imagebuilder get-image \
        --image-build-version-arn "$execution_arn" \
        --query 'image.state.status' \
        --output text 2>/dev/null)

    # If the command failed or returned empty, check if it's still building
    if [ $? -ne 0 ] || [ -z "$status" ] || [ "$status" = "None" ]; then
        # Try to list images to see if it exists but is still building
        local image_exists=$(aws imagebuilder list-images \
            --filters "name=name,values=$(echo "$execution_arn" | cut -d'/' -f2)" \
            --query 'imageVersionList[0].arn' \
            --output text 2>/dev/null)

        if [ -n "$image_exists" ] && [ "$image_exists" != "None" ]; then
            echo "BUILDING"
        else
            echo "PENDING"
        fi
    else
        echo "$status"
    fi
}

# Function to get AMI ID from completed execution
get_ami_id() {
    local execution_arn="$1"

    # Get the AMI ID from the completed image
    aws imagebuilder get-image \
        --image-build-version-arn "$execution_arn" \
        --query 'image.outputResources.amis[0].image' \
        --output text 2>/dev/null || echo ""
}

# Function to get pipeline name from ARN
get_pipeline_name() {
    local pipeline_arn="$1"
    echo "$pipeline_arn" | sed 's/.*\/\([^\/]*\)$/\1/'
}

# Function to use previous manifest file from Parameter Store when build is skipped
use_previous_manifest() {
    echo "=== Using Previous AMI Manifest from Parameter Store ==="

    local parameter_name="/idea/pipeline/ami-manifest/$RELEASE_VERSION"
    local manifest_file="$CODEBUILD_SRC_DIR/ami_manifest.json"

    echo "Checking for previous manifest at parameter: $parameter_name"

    # Try to get the previous manifest from Parameter Store
    if aws ssm get-parameter --name "$parameter_name" --query 'Parameter.Value' --output text > "$manifest_file" 2>/dev/null; then
        echo "✓ Successfully retrieved previous manifest from Parameter Store"

        # Update the manifest with current timestamp and skip information
        local temp_manifest="/tmp/updated_manifest.json"

        # Read the existing manifest and update it
        if command -v jq >/dev/null 2>&1; then
            # Use jq if available for proper JSON manipulation
            jq --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
               --arg local_md5 "$LOCAL_MD5" \
               --arg s3_md5 "$S3_MD5" \
               '. + {
                   "timestamp": $timestamp,
                   "build_skipped": true,
                   "reason": "No changes detected in res-installation-scripts.tar.gz",
                   "local_md5": $local_md5,
                   "s3_md5": $s3_md5,
                   "using_previous_manifest": true
               }' "$manifest_file" > "$temp_manifest"
            mv "$temp_manifest" "$manifest_file"
        else
            # Fallback: manually update the manifest (less robust but works without jq)
            echo "jq not available, manually updating manifest..."

            # Create a backup and update manually
            cp "$manifest_file" "$temp_manifest"

            # Remove the closing brace and add our new fields
            sed -i '$ s/}$//' "$manifest_file"

            # Add the new fields
            echo '  ,' >> "$manifest_file"
            echo '  "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",' >> "$manifest_file"
            echo '  "build_skipped": true,' >> "$manifest_file"
            echo '  "reason": "No changes detected in res-installation-scripts.tar.gz",' >> "$manifest_file"
            echo '  "local_md5": "'$LOCAL_MD5'",' >> "$manifest_file"
            echo '  "s3_md5": "'$S3_MD5'",' >> "$manifest_file"
            echo '  "using_previous_manifest": true' >> "$manifest_file"
            echo '}' >> "$manifest_file"
        fi

        echo "Updated manifest with current build information:"
        cat "$manifest_file"

        # Extract summary information from the manifest
        local total_amis=$(grep -o '"total_amis": [0-9]*' "$manifest_file" | grep -o '[0-9]*' || echo "0")
        local successful_amis=$(grep -o '"successful_amis": [0-9]*' "$manifest_file" | grep -o '[0-9]*' || echo "0")

        # Extract infrastructure AMI IDs
        local infra_ami_ids=()
        if command -v jq >/dev/null 2>&1; then
            # Use jq to extract infrastructure AMI IDs
            while IFS= read -r ami_id; do
                if [ -n "$ami_id" ] && [ "$ami_id" != "null" ]; then
                    infra_ami_ids+=("$ami_id")
                fi
            done < <(jq -r '.amis[] | select(.is_infrastructure == true) | .ami_id' "$manifest_file" 2>/dev/null)
        else
            # Fallback: grep for infrastructure AMIs
            while IFS= read -r line; do
                if [[ "$line" == *'"is_infrastructure": true'* ]]; then
                    # Look backwards for the ami_id in this AMI block
                    local ami_id=$(echo "$line" | grep -B 10 '"is_infrastructure": true' | grep '"ami_id"' | tail -1 | sed 's/.*"ami_id": "\([^"]*\)".*/\1/')
                    if [ -n "$ami_id" ]; then
                        infra_ami_ids+=("$ami_id")
                    fi
                fi
            done < "$manifest_file"
        fi

        echo "AMI Build Summary (Using Previous Manifest):"
        echo "- Total AMIs: $successful_amis"
        if [ ${#infra_ami_ids[@]} -gt 0 ]; then
            echo "- Infrastructure AMIs: ${infra_ami_ids[*]}"
        else
            echo "- Infrastructure AMIs: None found"
        fi
        echo "- Region: $AWS_DEFAULT_REGION"
        echo "- Build timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        echo "- Using previous manifest from Parameter Store"

        echo "AMI Build Stage completed (using previous manifest)!"
        echo "AMI manifest file available for next stage: ami_manifest.json"

    else
        echo "⚠ Previous manifest not found in Parameter Store, this might be the first build"
        echo "Creating minimal manifest indicating no previous build available"

        # Create a minimal manifest indicating no previous build was available
        echo "{" > "$manifest_file"
        echo '  "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",' >> "$manifest_file"
        echo '  "region": "'$AWS_DEFAULT_REGION'",' >> "$manifest_file"
        echo '  "build_skipped": true,' >> "$manifest_file"
        echo '  "reason": "No changes detected in res-installation-scripts.tar.gz",' >> "$manifest_file"
        echo '  "local_md5": "'$LOCAL_MD5'",' >> "$manifest_file"
        echo '  "s3_md5": "'$S3_MD5'",' >> "$manifest_file"
        echo '  "using_previous_manifest": false,' >> "$manifest_file"
        echo '  "previous_manifest_not_found": true,' >> "$manifest_file"
        echo '  "total_amis": 0,' >> "$manifest_file"
        echo '  "successful_amis": 0,' >> "$manifest_file"
        echo '  "amis": []' >> "$manifest_file"
        echo "}" >> "$manifest_file"

        echo "AMI Build Stage completed (no previous manifest available)!"
        echo "AMI manifest file available for next stage: ami_manifest.json"
    fi
}

# Main execution
main() {
    echo "Starting AMI Build Stage..."

    # Upload build scripts and host Python applications required by image builder
    export AWS_ACCOUNT=$(echo $CODEBUILD_BUILD_ARN | cut -f5 -d ':')
    COMMIT_ID=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -b -8)
    RELEASE_VERSION=$(echo "$(<RES_VERSION.txt )" | xargs)

    SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
    DIST_DIR=${SCRIPT_DIR}/../../../../../dist/

    echo "Packaging build scripts and host Python applications..."
    invoke package.res-installation-scripts

    # Check if the local res-installation-scripts.tar.gz differs from the one in staging bucket
    LOCAL_TARBALL="${DIST_DIR}res-installation-scripts.tar.gz"
    S3_TARBALL_PATH="s3://${STAGING_BUCKET_NAME}/releases/$RELEASE_VERSION/res-installation-scripts.tar.gz"

    echo "Checking if AMI build is needed..."
    echo "Local tarball: $LOCAL_TARBALL"
    echo "S3 tarball path: $S3_TARBALL_PATH"

    # Calculate MD5 hash of local file
    if [ ! -f "$LOCAL_TARBALL" ]; then
        echo "ERROR: Local res-installation-scripts.tar.gz not found at $LOCAL_TARBALL"
        exit 1
    fi

    LOCAL_MD5=$(md5sum "$LOCAL_TARBALL" | cut -d' ' -f1)
    echo "Local MD5: $LOCAL_MD5"

    # Check if S3 object exists and get its MD5
    S3_MD5=""
    if aws s3api head-object --bucket "${STAGING_BUCKET_NAME}" --key "releases/$RELEASE_VERSION/res-installation-scripts.tar.gz" >/dev/null 2>&1; then
        # Get ETag from S3 object (which is MD5 for single-part uploads)
        S3_ETAG=$(aws s3api head-object --bucket "${STAGING_BUCKET_NAME}" --key "releases/$RELEASE_VERSION/res-installation-scripts.tar.gz" --query 'ETag' --output text | tr -d '"')

        # ETag might be MD5 or might be a multipart upload hash
        # For single-part uploads, ETag is the MD5 hash
        # For multipart uploads, ETag contains a dash (e.g., "hash-partcount")
        if [[ "$S3_ETAG" != *"-"* ]]; then
            S3_MD5="$S3_ETAG"
            echo "S3 MD5 (from ETag): $S3_MD5"
        else
            echo "S3 object was uploaded as multipart, downloading to compare..."
            # Download the S3 file to a temporary location and calculate MD5
            TEMP_S3_FILE="/tmp/s3-res-installation-scripts.tar.gz"
            aws s3 cp "$S3_TARBALL_PATH" "$TEMP_S3_FILE"
            S3_MD5=$(md5sum "$TEMP_S3_FILE" | cut -d' ' -f1)
            rm -f "$TEMP_S3_FILE"
            echo "S3 MD5 (calculated): $S3_MD5"
        fi
    else
        echo "S3 object does not exist, AMI build is needed"
    fi

    # Compare MD5 hashes
    if [ -n "$S3_MD5" ] && [ "$LOCAL_MD5" = "$S3_MD5" ]; then
        echo "Local and S3 res-installation-scripts.tar.gz are identical (MD5: $LOCAL_MD5)"
        echo "Skipping AMI build as no changes detected in installation scripts"
        echo "Using previous AMI manifest from Parameter Store..."

        # Download and use the previous manifest file from S3
        use_previous_manifest
        exit 0
    else
        echo "Local and S3 res-installation-scripts.tar.gz differ or S3 object doesn't exist"
        echo "Proceeding with AMI build..."

        # Upload the new version to S3
        echo "Uploading updated build scripts..."
        aws s3 cp ${DIST_DIR} s3://${STAGING_BUCKET_NAME}/releases/$RELEASE_VERSION/ --recursive --exclude "*" --include "*.tar.gz"
        echo "Build scripts uploaded successfully. Proceeding with AMI builds..."
    fi

    echo "=== AMI Build Main Execution Starting ==="

    # Get the nested stack name for PrebakedRESReadyAMIsStack
    echo "Step 1: Getting main stack ID..."
    local main_stack_id
    if ! main_stack_id=$(aws cloudformation describe-stacks \
        --stack-name RESBuildPipelineStack \
        --query "Stacks[0].StackId" \
        --output text 2>&1); then
        echo "ERROR: Failed to get main stack ID for RESBuildPipelineStack" >&2
        echo "AWS CLI Error: $main_stack_id" >&2
        echo "This could be due to:" >&2
        echo "  - Stack doesn't exist" >&2
        echo "  - Insufficient CloudFormation permissions" >&2
        echo "  - Wrong region or account" >&2
        exit 1
    fi

    if [ -z "$main_stack_id" ] || [ "$main_stack_id" = "None" ]; then
        echo "ERROR: Main stack ID is empty or None" >&2
        exit 1
    fi

    echo "✓ Main stack ID: $main_stack_id"

    # Find the nested stack
    echo "Step 2: Finding AMIBuildStack nested stack..."
    local nested_stack_name
    if ! nested_stack_name=$(aws cloudformation describe-stacks \
        --query "Stacks[?ParentId=='$main_stack_id' && contains(StackName, 'AMIBuild')].StackName | [0]" \
        --output text 2>&1); then
        echo "ERROR: Failed to find nested stacks" >&2
        echo "AWS CLI Error: $nested_stack_name" >&2
        echo "This could be due to:" >&2
        echo "  - Insufficient CloudFormation ListStacks permissions" >&2
        echo "  - Main stack has no nested stacks" >&2
        exit 1
    fi

    if [ -z "$nested_stack_name" ] || [ "$nested_stack_name" = "None" ]; then
        echo "ERROR: Could not find AMIBuildStack nested stack" >&2
        echo "Available nested stacks for parent $main_stack_id:" >&2
        aws cloudformation describe-stacks \
            --query "Stacks[?ParentId=='$main_stack_id'].[StackName,StackStatus]" \
            --output table 2>/dev/null || echo "  (Failed to list nested stacks)" >&2
        exit 1
    fi

    echo "✓ Found nested stack: $nested_stack_name"

    # Get all pipeline ARNs
    echo "Step 3: Getting Image Builder pipeline ARNs..."
    local pipeline_arns_result
    if ! pipeline_arns_result=$(get_pipeline_arns "$nested_stack_name"); then
        echo "ERROR: Failed to get pipeline ARNs from nested stack" >&2
        exit 1
    fi

    local pipeline_arns=($pipeline_arns_result)

    if [ ${#pipeline_arns[@]} -eq 0 ]; then
        echo "ERROR: No image pipelines found in stack $nested_stack_name" >&2
        echo "Available resources in stack:" >&2
        aws cloudformation describe-stack-resources \
            --stack-name "$nested_stack_name" \
            --query 'StackResources[].[ResourceType,LogicalResourceId,PhysicalResourceId]' \
            --output table 2>/dev/null || echo "  (Failed to list stack resources)" >&2
        exit 1
    fi

    echo "Found ${#pipeline_arns[@]} image pipelines"

    # Trigger all pipelines and collect execution ARNs
    local executions=()
    local pipeline_names=()

    # TODO: Remove ubuntu2404 skip once Canonical EC2 archive mirror issue is resolved.
    #       Tracking: https://status.canonical.com (Ubuntu Developer Tools Outage, open since Jul 15 2026)
    local SKIP_PIPELINES=("ubuntu2404")

    for pipeline_arn in "${pipeline_arns[@]}"; do
        if [ -n "$pipeline_arn" ]; then
            # Skip pipelines matching the skip list
            local pipeline_name_check
            pipeline_name_check=$(get_pipeline_name "$pipeline_arn")
            local skip=false
            for skip_pattern in "${SKIP_PIPELINES[@]}"; do
                if [[ "$pipeline_name_check" == *"$skip_pattern"* ]]; then
                    echo "Skipping pipeline $pipeline_name_check (matches skip pattern: $skip_pattern)" >&2
                    skip=true
                    break
                fi
            done
            if [ "$skip" = true ]; then
                continue
            fi
            local execution_arn
            if ! execution_arn=$(trigger_pipeline "$pipeline_arn"); then
                echo "ERROR: Failed to trigger pipeline $pipeline_arn, skipping" >&2
                continue
            fi
            executions+=("$execution_arn")
            pipeline_names+=("$pipeline_name_check")
        fi
    done

    echo "Triggered ${#executions[@]} pipeline executions"

    if [ ${#executions[@]} -eq 0 ]; then
        echo "ERROR: No pipeline executions were triggered" >&2
        exit 1
    fi

    # Wait for all executions to complete
    local max_wait_time=7200  # 2 hours
    local check_interval=60   # 1 minute
    local elapsed_time=0

    echo "Waiting for all pipelines to complete..."

    while [ $elapsed_time -lt $max_wait_time ]; do
        local completed=0
        local failed=0
        local in_progress=0

        for i in "${!executions[@]}"; do
            local execution_arn="${executions[$i]}"
            echo "Execution ARN $execution_arn" >&2
            local pipeline_name="${pipeline_names[$i]}"
            echo "Pipeline $pipeline_name" >&2

            # Get pipeline status with error handling for CodeBuild compatibility
            local pipeline_status
            pipeline_status=$(check_execution_status "$execution_arn" 2>/dev/null) || pipeline_status="PENDING"
            echo "Pipeline $pipeline_name status: $pipeline_status" >&2

            case "$pipeline_status" in
                "AVAILABLE")
                    completed=$((completed + 1))
                    ;;
                "FAILED"|"CANCELLED"|"DEPRECATED")
                    echo "Pipeline $pipeline_name failed with status: $pipeline_status" >&2
                    failed=$((failed + 1))
                    ;;
                *)
                    in_progress=$((in_progress + 1))
                    ;;
            esac
        done

        echo "Status: $completed completed, $in_progress in progress, $failed failed"

        if [ $failed -gt 0 ]; then
            echo "Some pipelines failed. Continuing to wait for remaining pipelines..." >&2
            # Don't exit immediately, let other pipelines complete
        fi

        if [ $completed -eq ${#executions[@]} ]; then
            echo "All pipelines completed successfully!"
            break
        fi

        # If we have some completed and some failed, but no in-progress, break
        if [ $in_progress -eq 0 ] && [ $((completed + failed)) -eq ${#executions[@]} ]; then
            echo "All pipelines finished (some may have failed)"
            break
        fi

        sleep $check_interval
        elapsed_time=$((elapsed_time + check_interval))
    done

    if [ $elapsed_time -ge $max_wait_time ]; then
        echo "ERROR: Timeout waiting for pipelines to complete; $in_progress still in progress" >&2
        exit 1
    fi

    # Fail the stage if any pipelines ended in a failed state
    if [ "$failed" -gt 0 ]; then
        echo "ERROR: $failed pipeline(s) ended in a failed state" >&2
        exit 1
    fi

    # Extract infrastructure AMI IDs for deployment stage
    echo "Extracting infrastructure AMI IDs..."

    # Find all infrastructure AMIs (pipelines with "infra" in the name)
    local infra_ami_ids=()

    for i in "${!executions[@]}"; do
        local execution_arn="${executions[$i]}"
        local pipeline_name="${pipeline_names[$i]}"
        local ami_id=$(get_ami_id "$execution_arn")

        # Check if this is an infrastructure pipeline (contains "infra" in the name)
        if [[ "$pipeline_name" == *"infra"* ]] && [ -n "$ami_id" ] && [ "$ami_id" != "None" ]; then
            infra_ami_ids+=("$ami_id")
            echo "Found infrastructure AMI: $pipeline_name -> $ami_id"
        fi
    done

    # Generate consolidated JSON manifest file with AMI IDs
    echo "Generating consolidated AMI manifest..."

    local manifest_file="$CODEBUILD_SRC_DIR/ami_manifest.json"
    echo "{" > "$manifest_file"
    echo '  "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",' >> "$manifest_file"
    echo '  "region": "'$AWS_DEFAULT_REGION'",' >> "$manifest_file"
    echo '  "total_amis": '${#executions[@]}',' >> "$manifest_file"
    echo '  "amis": [' >> "$manifest_file"

    if [ ${#infra_ami_ids[@]} -gt 0 ]; then
        echo "Infrastructure AMI IDs: ${infra_ami_ids[*]}"
    else
        echo "Warning: No infrastructure AMIs found in the build results"
    fi

    local first=true
    local successful_amis=0
    for i in "${!executions[@]}"; do
        local execution_arn="${executions[$i]}"
        local pipeline_name="${pipeline_names[$i]}"
        local ami_id=$(get_ami_id "$execution_arn")

        if [ -n "$ami_id" ] && [ "$ami_id" != "None" ]; then

            # Determine OS type from pipeline name
            local os_type=""
            if [[ "$pipeline_name" == *"al2023"* ]] || [[ "$pipeline_name" == *"amzn2023"* ]]; then
                os_type="amzn2023"
            elif [[ "$pipeline_name" == *"rhel9"* ]]; then
                os_type="rhel9"
            elif [[ "$pipeline_name" == *"ubuntu2204"* ]]; then
                os_type="ubuntu2204"
            elif [[ "$pipeline_name" == *"ubuntu2404"* ]]; then
                os_type="ubuntu2404"
            elif [[ "$pipeline_name" == *"rocky9"* ]]; then
                os_type="rocky9"
            elif [[ "$pipeline_name" == *"windows"* ]]; then
                os_type="windows"
            fi

            # Determine architecture from pipeline name
            local arch_type="x86-64"  # Default
            if [[ "$pipeline_name" == *"arm64"* ]]; then
                arch_type="arm64"
            fi

            if [ "$first" = false ]; then
                echo "," >> "$manifest_file"
            fi
            echo "    {" >> "$manifest_file"
            echo '      "pipeline_name": "'$pipeline_name'",' >> "$manifest_file"
            echo '      "ami_id": "'$ami_id'",' >> "$manifest_file"
            echo '      "region": "'$AWS_DEFAULT_REGION'",' >> "$manifest_file"
            echo '      "os_type": "'$os_type'",' >> "$manifest_file"
            echo '      "architecture": "'$arch_type'",' >> "$manifest_file"
            # Check if this AMI ID is in the infrastructure AMIs array
            local is_infra="false"
            for infra_id in "${infra_ami_ids[@]}"; do
                if [ "$ami_id" = "$infra_id" ]; then
                    is_infra="true"
                    break
                fi
            done
            echo '      "is_infrastructure": '$is_infra >> "$manifest_file"
            echo -n "    }" >> "$manifest_file"
            first=false
            successful_amis=$((successful_amis + 1))
        fi
    done

    echo "" >> "$manifest_file"
    echo "  ]," >> "$manifest_file"
    echo '  "successful_amis": '$successful_amis >> "$manifest_file"
    echo "}" >> "$manifest_file"

    echo "Consolidated AMI manifest generated with $successful_amis successful AMIs:"
    cat "$manifest_file"

    echo "Consolidated JSON manifest created at: $manifest_file"

    # Display summary of all AMIs from the manifest
    echo "AMI Build Summary:"
    echo "- Total AMIs built: $successful_amis"
    if [ ${#infra_ami_ids[@]} -gt 0 ]; then
        echo "- Infrastructure AMIs: ${infra_ami_ids[*]}"
    else
        echo "- Infrastructure AMIs: None found"
    fi
    echo "- Region: $AWS_DEFAULT_REGION"
    echo "- Build timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "- Config file will be updated in separate Config Update stage"

    # Store the manifest file in Parameter Store for future use
    echo "Storing AMI manifest in Parameter Store..."
    local parameter_name="/idea/pipeline/ami-manifest/$RELEASE_VERSION"

    # Use advanced-tier parameter to support larger values (up to 8KB)
    if aws ssm put-parameter --name "$parameter_name" --value "$(cat "$manifest_file")" --type "String" --tier "Advanced" --overwrite; then
        echo "✓ Successfully stored manifest in Parameter Store (Advanced tier): $parameter_name"
    else
        echo "⚠ Failed to store manifest in Parameter Store, but continuing..."
    fi

    echo "AMI Build Stage completed successfully!"
    echo "AMI manifest file available for next stage: ami_manifest.json"
}

# Execute main function
main "$@"
