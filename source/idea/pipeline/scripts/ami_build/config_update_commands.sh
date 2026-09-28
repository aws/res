#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

set -e

echo "Starting Software Stack Config Update..."

# Check if consolidated AMI manifest exists from AMI build step
if [ -f "ami_manifest.json" ]; then
    echo "Found consolidated AMI manifest file"
    cat ami_manifest.json

    # Update base software stack config with new AMI IDs
    echo "Updating base software stack config with new AMI IDs..."

    config_file="source/idea/infrastructure/resources/config/base-software-stack-config.yaml"
    original_config_file="source/idea/infrastructure/resources/config/base-software-stack-config.yaml.original"
    updated_config_file="source/idea/infrastructure/resources/config/base-software-stack-config-updated.yaml"
    current_region=$(jq -r '.region' ami_manifest.json)

    # Create backup of original config file if it doesn't exist
    if [ ! -f "$original_config_file" ]; then
        echo "Creating backup of original VDI config file: $original_config_file"
        cp "$config_file" "$original_config_file"
    fi

    # Copy original config file for updating
    cp "$config_file" "$updated_config_file"

    # Process each AMI from the manifest (only non-infrastructure AMIs for VDI)
    jq -r '.amis[] | select(.is_infrastructure == false) | @base64' ami_manifest.json | while IFS= read -r ami_data; do
        ami_info=$(echo "$ami_data" | base64 --decode)
        pipeline_name=$(echo "$ami_info" | jq -r '.pipeline_name')
        ami_id=$(echo "$ami_info" | jq -r '.ami_id')
        is_infrastructure=$(echo "$ami_info" | jq -r '.is_infrastructure')

        # Extract structured information from manifest
        os_type=$(echo "$ami_info" | jq -r '.os_type // empty')
        arch_type=$(echo "$ami_info" | jq -r '.architecture // "x86-64"')

        echo "Processing VDI AMI: $pipeline_name -> $ami_id (OS: $os_type, Architecture: $arch_type)"

        # Update the AMI ID in the config file for the current region
        if [ -n "$os_type" ]; then
            echo "Updating $os_type/$arch_type AMI ID for region $current_region: $ami_id"

            # Use yq to update the YAML file (if available) or sed as fallback
            if command -v yq >/dev/null 2>&1; then
                yq eval ".$os_type.$arch_type.$current_region[0].\"ami-id\" = \"$ami_id\"" -i "$updated_config_file"
            else
                # Fallback to sed for basic replacement
                sed -i.bak "/^$os_type:/,/^[a-zA-Z]/ { /$arch_type:/,/^  [a-zA-Z]/ { /^    $current_region:/,/^    [a-zA-Z-]/ { s/ami-id: ami-[a-f0-9]*/ami-id: $ami_id/; }; }; }" "$updated_config_file"
            fi
        else
            echo "Warning: Could not determine OS type for pipeline: $pipeline_name"
        fi
    done

    # Replace the original config file with the updated one
    mv "$updated_config_file" "$config_file"
    echo "Base software stack config updated with new VDI AMI IDs"

    # Update infrastructure AMI configuration
    echo "Updating infrastructure AMI configuration..."
    
    infra_config_file="source/idea/infrastructure/resources/config/region_ami_config.yml"
    original_infra_config_file="source/idea/infrastructure/resources/config/region_ami_config.yml.original"
    
    # Create backup of original infrastructure config file if it doesn't exist
    if [ ! -f "$original_infra_config_file" ]; then
        echo "Creating backup of original infrastructure config file: $original_infra_config_file"
        cp "$infra_config_file" "$original_infra_config_file"
    fi
    
    # Process infrastructure AMIs from the manifest
    jq -r '.amis[] | select(.is_infrastructure == true) | @base64' ami_manifest.json | while IFS= read -r ami_data; do
        ami_info=$(echo "$ami_data" | base64 --decode)
        pipeline_name=$(echo "$ami_info" | jq -r '.pipeline_name')
        ami_id=$(echo "$ami_info" | jq -r '.ami_id')
        os_type=$(echo "$ami_info" | jq -r '.os_type // "amzn2023"')
        
        echo "Processing Infrastructure AMI: $pipeline_name -> $ami_id (OS: $os_type)"
        
        # Update the infrastructure AMI ID in the region config file for the current region
        if [ -f "$infra_config_file" ]; then
            echo "Updating infrastructure AMI ID for region $current_region: $ami_id"
            
            # Use yq to update the YAML file (if available) or sed as fallback
            if command -v yq >/dev/null 2>&1; then
                # Use yq for precise YAML manipulation
                yq eval ".$current_region.$os_type = \"$ami_id\"" -i "$infra_config_file"
            else
                # Fallback to sed for basic replacement
                sed -i.bak "/^$current_region:/,/^[a-zA-Z]/ { s/  $os_type: ami-[a-f0-9]*/  $os_type: $ami_id/; }" "$infra_config_file"
            fi
            
            echo "Infrastructure AMI config updated: $infra_config_file"
        else
            echo "Warning: Infrastructure config file not found: $infra_config_file"
        fi
    done

    # Display summary
    echo "Config Update Summary:"
    echo "- Total AMIs in manifest: $(jq -r '.successful_amis' ami_manifest.json)"
    echo "- VDI AMIs processed: $(jq -r '[.amis[] | select(.is_infrastructure == false)] | length' ami_manifest.json)"
    echo "- Infrastructure AMIs processed: $(jq -r '[.amis[] | select(.is_infrastructure == true)] | length' ami_manifest.json)"
    echo "- Region: $current_region"
    echo "- VDI config file updated: $config_file"
    echo "- Infrastructure config file updated: $infra_config_file"

else
    echo "No AMI manifest file found, skipping config update"
fi

echo "Software Stack Config Update completed successfully!"
