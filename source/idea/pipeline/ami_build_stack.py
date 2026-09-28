#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, Dict, List

import yaml
from aws_cdk import CfnOutput, NestedStack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_imagebuilder as imagebuilder
from constructs import Construct

# Apache 2.0 license header shared across all Image Builder component YAML definitions.
_COMPONENT_LICENSE_HEADER = """\
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
"""

# Standard block device mapping for all Image Builder recipes (50 GB gp3).
_BLOCK_DEVICE_MAPPINGS = [
    {
        "deviceName": "/dev/sda1",
        "ebs": {
            "deleteOnTermination": True,
            "volumeSize": 50,
            "volumeType": "gp3",
        },
    }
]


class AMIBuildStack(NestedStack):

    def __init__(
        self, scope: Construct, construct_id: str, staging_bucket: str, **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Read RES version
        from idea.infrastructure.install.constructs.base import ResBaseConstruct

        res_version = ResBaseConstruct.get_res_release_version()

        # Component version derived from RES version (must be semver x.x.x)
        # RES version "2026.06" becomes "2026.6.0"
        res_version_parts = res_version.split(".")
        component_version = f"{res_version_parts[0]}.{int(res_version_parts[1])}.0"

        # Get proxy configuration from context
        http_proxy = (self.node.try_get_context("HttpProxy") or "").strip('"')
        https_proxy = (self.node.try_get_context("HttpsProxy") or "").strip('"')
        no_proxy = (self.node.try_get_context("NoProxy") or "").strip('"')

        # Load AMI configurations
        vdi_os_config = self._load_config("base-software-stack-config.yaml", "VDI")
        infra_ami_config = self._load_config("region_ami_config.yml", "Infrastructure")

        # Image Builder infrastructure (IAM role, instance profile, infra configs)
        instance_profile, infrastructure_config, arm64_infrastructure_config = (
            self._create_image_builder_infrastructure()
        )

        # Distribution configuration (shared across all pipelines)
        distribution_config = self._create_distribution_config()

        # Image Builder components
        components = self._create_components(
            staging_bucket,
            res_version,
            component_version,
            http_proxy,
            https_proxy,
            no_proxy,
        )

        # Read target region from CDK context or environment.
        # In pipeline self-mutation, self.region may be a CFN token if env is not
        # explicitly set on the nested stack. AWS_DEFAULT_REGION is set by the synth
        # step as a concrete string.
        target_region = self.node.try_get_context("target_region") or os.environ.get(
            "AWS_DEFAULT_REGION", ""
        )
        if not target_region:
            raise ValueError(
                "Cannot determine target region for AMI config lookup. "
                "Set CDK context 'target_region' or AWS_DEFAULT_REGION env var."
            )

        # Create VDI pipelines
        vdi_pipelines = self._create_vdi_pipelines(
            vdi_os_config,
            target_region,
            components,
            infrastructure_config,
            arm64_infrastructure_config,
            distribution_config,
            component_version,
        )

        # Create Infrastructure pipelines
        infra_pipelines = self._create_infra_pipelines(
            infra_ami_config,
            target_region,
            components["Infrastructure"],
            infrastructure_config,
            distribution_config,
            component_version,
        )

        # Add dependencies for all infrastructure configurations
        infrastructure_config.add_dependency(instance_profile)
        arm64_infrastructure_config.add_dependency(instance_profile)

        # Output pipeline information
        CfnOutput(
            self,
            "TotalPipelinesCreated",
            value=str(len(vdi_pipelines) + len(infra_pipelines)),
            description="Total number of Image Builder pipelines created (VDI + Infrastructure)",
        )

    # -------------------------------------------------------------------------
    # Configuration loading
    # -------------------------------------------------------------------------

    @staticmethod
    def _load_config(filename: str, label: str) -> Dict[str, Any]:
        """Load a YAML config file, preferring the .original backup if it exists."""
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "infrastructure",
            "resources",
            "config",
            filename,
        )
        original_path = config_path + ".original"

        if os.path.exists(original_path):
            print(f"Loading {label} base AMI IDs from original config: {original_path}")
            path_to_load = original_path
        else:
            print(
                f"Original {label} config not found, using current config: {config_path}"
            )
            path_to_load = config_path

        with open(path_to_load, "r") as file:
            result: Dict[str, Any] = yaml.safe_load(file)
            return result

    # -------------------------------------------------------------------------
    # Image Builder infrastructure (IAM, instance profile, infra configs)
    # -------------------------------------------------------------------------

    def _create_image_builder_infrastructure(self) -> tuple[Any, Any, Any]:
        """Create IAM role, instance profile, and infrastructure configurations."""
        image_builder_role = iam.Role(
            self,
            "RES-EC2InstanceProfileForImageBuilder",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonS3ReadOnlyAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "EC2InstanceProfileForImageBuilder"
                ),
            ],
            inline_policies={
                "SSMGetParameter": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["ssm:GetParameter"],
                            resources=[
                                f"arn:{self.partition}:ssm:{self.region}:{self.account}:parameter/*",
                            ],
                        )
                    ]
                )
            },
        )

        instance_profile = iam.CfnInstanceProfile(
            self,
            "ImageBuilderInstanceProfile",
            roles=[image_builder_role.role_name],
        )

        # Image Builder uses the default VPC automatically when no subnet/SG is specified.
        # We omit explicit VPC configuration to avoid from_lookup which requires
        # account/region at the stack level (not available during pipeline self-mutation synth).
        instance_profile_name = instance_profile.ref

        infrastructure_config = imagebuilder.CfnInfrastructureConfiguration(
            self,
            "RESImageBuilderInfraConfig",
            name="res-image-builder-infrastructure",
            instance_profile_name=instance_profile_name,
            instance_types=["t3.medium"],
            terminate_instance_on_failure=True,
            description="Default infrastructure configuration for RES Image Builder",
        )

        arm64_infrastructure_config = imagebuilder.CfnInfrastructureConfiguration(
            self,
            "RESImageBuilderARM64InfraConfig",
            name="res-image-builder-infrastructure-arm64",
            instance_profile_name=instance_profile_name,
            instance_types=["m6g.medium"],
            terminate_instance_on_failure=True,
            description="ARM64 infrastructure configuration for RES Image Builder",
        )

        return instance_profile, infrastructure_config, arm64_infrastructure_config

    # -------------------------------------------------------------------------
    # Distribution configuration
    # -------------------------------------------------------------------------

    def _create_distribution_config(self) -> imagebuilder.CfnDistributionConfiguration:
        """Create the shared distribution configuration for all pipelines."""
        return imagebuilder.CfnDistributionConfiguration(
            self,
            "RESDistributionConfig",
            name="res-distribution-config",
            distributions=[
                {
                    "region": self.region,
                    "amiDistributionConfiguration": {
                        "name": "RES-Ready-AMI-{{ imagebuilder:buildDate }}",
                        "description": "RES-ready AMI built with Image Builder",
                        "amiTags": {
                            "Name": "RES-Ready-AMI",
                            "CreatedBy": "EC2-Image-Builder",
                            "Purpose": "RES",
                        },
                    },
                }
            ],
        )

    # -------------------------------------------------------------------------
    # Image Builder components
    # -------------------------------------------------------------------------

    def _create_components(
        self,
        staging_bucket: str,
        res_version: str,
        component_version: str,
        http_proxy: str,
        https_proxy: str,
        no_proxy: str,
    ) -> Dict[str, imagebuilder.CfnComponent]:
        """Create all Image Builder components (Linux VDI, Windows VDI, Infrastructure)."""
        components: Dict[str, imagebuilder.CfnComponent] = {}

        components["LinuxVDI"] = imagebuilder.CfnComponent(
            self,
            "RESLinuxVDIComponent",
            name="research-and-engineering-studio-vdi-linux",
            platform="Linux",
            version=component_version,
            description="An RES EC2 Image Builder component to install required RES software dependencies for Linux VDI.",
            data=self._linux_vdi_component_data(staging_bucket, res_version),
        )

        components["WindowsVDI"] = imagebuilder.CfnComponent(
            self,
            "RESWindowsVDIComponent",
            name="research-and-engineering-studio-vdi-windows",
            platform="Windows",
            version=component_version,
            description="An RES EC2 Image Builder component to install required RES software dependencies for Windows VDI.",
            data=self._windows_vdi_component_data(staging_bucket, res_version),
        )

        components["Infrastructure"] = imagebuilder.CfnComponent(
            self,
            "RESInfrastructureComponent",
            name="research-and-engineering-studio-infrastructure",
            platform="Linux",
            version=component_version,
            description="An RES EC2 Image Builder component to install required RES software dependencies for infrastructure hosts.",
            data=self._infrastructure_component_data(
                staging_bucket, res_version, http_proxy, https_proxy, no_proxy
            ),
        )

        return components

    @staticmethod
    def _linux_vdi_component_data(staging_bucket: str, res_version: str) -> str:
        return f"""{_COMPONENT_LICENSE_HEADER}
name: research-and-engineering-studio-vdi-linux
description: An RES EC2 Image Builder component to install required RES software dependencies for Linux VDI.
schemaVersion: 1.0

parameters:
  - GPUFamily:
      type: string
      description: GPU family (NONE, NVIDIA, or AMD)
      default: NONE

phases:
  - name: build
    steps:
      - name: PrepareRESBootstrap
        action: ExecuteBash
        onFailure: Abort
        maxAttempts: 3
        inputs:
          commands:
            - "mkdir -p /root/bootstrap/logs"
            - "mkdir -p /root/bootstrap/latest"

      - name: DownloadRESLinuxInstallPackage
        action: S3Download
        onFailure: Abort
        maxAttempts: 3
        inputs:
          - source: "s3://{staging_bucket}/releases/{res_version}/res-installation-scripts.tar.gz"
            destination: "/root/bootstrap/res-installation-scripts/res-installation-scripts.tar.gz"

      - name: RunInstallScript
        action: ExecuteBash
        onFailure: Abort
        maxAttempts: 3
        inputs:
          commands:
            - "cd /root/bootstrap/res-installation-scripts"
            - "tar -xf res-installation-scripts.tar.gz"
            - "cd scripts/virtual-desktop-host/linux"
            - "/bin/bash install.sh -g {{{{ GPUFamily }}}}"

      - name: RunInstallPostRebootScript
        action: ExecuteBash
        onFailure: Abort
        maxAttempts: 3
        inputs:
          commands:
            - "cd /root/bootstrap/res-installation-scripts/scripts/virtual-desktop-host/linux"
            - 'sed -i ''/^export AWS_DEFAULT_PROFILE="bootstrap_profile"$/d'' install_post_reboot.sh'
            - "/bin/bash install_post_reboot.sh -g {{{{ GPUFamily }}}}"

      - name: PreventAL2023FromUninstallingCronie
        action: ExecuteBash
        onFailure: Abort
        maxAttempts: 3
        inputs:
          commands:
            - "rm -f /tmp/imagebuilder_service/crontab_installed"
"""

    @staticmethod
    def _windows_vdi_component_data(staging_bucket: str, res_version: str) -> str:
        return f"""{_COMPONENT_LICENSE_HEADER}
name: research-and-engineering-studio-vdi-windows
description: An RES EC2 Image Builder component to install required RES software dependencies for Windows VDI.
schemaVersion: 1.0

phases:
  - name: build
    steps:
       - name: CreateRESBootstrapFolder
         action: CreateFolder
         onFailure: Abort
         maxAttempts: 3
         inputs:
            - path: 'C:\\Users\\Administrator\\RES\\Bootstrap'
              overwrite: true

       - name: DownloadRESWindowsInstallPackage
         action: S3Download
         onFailure: Abort
         maxAttempts: 3
         inputs:
            - source: 's3://{staging_bucket}/releases/{res_version}/res-installation-scripts.tar.gz'
              destination: '{{{{ build.CreateRESBootstrapFolder.inputs[0].path }}}}\\res-installation-scripts.tar.gz'

       - name: RunInstallScript
         action: ExecutePowerShell
         onFailure: Abort
         maxAttempts: 3
         inputs:
            commands:
                - 'cd {{{{ build.CreateRESBootstrapFolder.inputs[0].path }}}}'
                - 'tar -xf res-installation-scripts.tar.gz'
                - 'Import-Module .\\scripts\\virtual-desktop-host\\windows\\Install.ps1'
                - 'Install-WindowsEC2Instance -PrebakeAMI'
"""

    def _infrastructure_component_data(
        self,
        staging_bucket: str,
        res_version: str,
        http_proxy: str,
        https_proxy: str,
        no_proxy: str,
    ) -> str:
        return f"""{_COMPONENT_LICENSE_HEADER}
name: research-and-engineering-studio-infrastructure
description: An RES EC2 Image Builder component to install required RES software dependencies for infrastructure hosts.
schemaVersion: 1.0

parameters:
  - AWSRegion:
      type: string
      description: RES Environment AWS Region

phases:
  - name: build
    steps:
       - name: DownloadRESInstallScripts
         action: S3Download
         onFailure: Abort
         maxAttempts: 3
         inputs:
            - source: 's3://{staging_bucket}/releases/{res_version}/res-installation-scripts.tar.gz'
              destination: '/root/bootstrap/res-installation-scripts/res-installation-scripts.tar.gz'

       - name: RunInstallScript
         action: ExecuteBash
         onFailure: Abort
         maxAttempts: 3
         inputs:
            commands:
                - 'cd /root/bootstrap/res-installation-scripts'
                - 'tar -xf res-installation-scripts.tar.gz'
                - 'cd scripts/infrastructure-host'
                - '/bin/bash install.sh'

       - name: AddEnvironmentVariables
         action: ExecuteBash
         onFailure: Abort
         maxAttempts: 3
         inputs:
            commands:
                - |
                  echo "# RES Infrastructure Host Environment Variables" >> /etc/environment
                  # Set up proxy configuration - resolve from SSM
                  HTTP_PROXY_VAL=$(aws ssm get-parameter --name "{http_proxy}" --query 'Parameter.Value' --output text --region {self.region} 2>/dev/null || echo "")
                  HTTPS_PROXY_VAL=$(aws ssm get-parameter --name "{https_proxy}" --query 'Parameter.Value' --output text --region {self.region} 2>/dev/null || echo "")
                  NO_PROXY_VAL=$(aws ssm get-parameter --name "{no_proxy}" --query 'Parameter.Value' --output text --region {self.region} 2>/dev/null || echo "")
                  echo "http_proxy=$HTTP_PROXY_VAL" >> /etc/environment
                  echo "https_proxy=$HTTPS_PROXY_VAL" >> /etc/environment
                  echo "no_proxy=$NO_PROXY_VAL" >> /etc/environment
"""

    # -------------------------------------------------------------------------
    # VDI pipelines
    # -------------------------------------------------------------------------

    def _create_vdi_pipelines(
        self,
        vdi_os_config: Dict[str, Any],
        target_region: str,
        components: Dict[str, Any],
        infrastructure_config: Any,
        arm64_infrastructure_config: Any,
        distribution_config: Any,
        component_version: str,
    ) -> List[Any]:
        """Create all VDI image recipes and pipelines."""
        pipelines = []
        for os_name, arch, ami_config, arch_data in self._iter_vdi_configs(
            vdi_os_config, target_region
        ):
            _, pipeline = self._create_vdi_pipeline(
                os_name=os_name,
                arch=arch,
                ami_config=ami_config,
                arch_data=arch_data,
                components=components,
                infrastructure_config=infrastructure_config,
                arm64_infrastructure_config=arm64_infrastructure_config,
                distribution_config=distribution_config,
                component_version=component_version,
            )
            pipelines.append(pipeline)
        return pipelines

    def _create_infra_pipelines(
        self,
        infra_ami_config: Dict[str, Any],
        target_region: str,
        infrastructure_component: Any,
        infrastructure_config: Any,
        distribution_config: Any,
        component_version: str,
    ) -> List[Any]:
        """Create all infrastructure image recipes and pipelines."""
        pipelines = []
        if target_region in infra_ami_config:
            for os_name, ami_id in infra_ami_config[target_region].items():
                if not ami_id:
                    continue
                _, pipeline = self._create_infra_pipeline(
                    os_name=os_name,
                    ami_id=ami_id,
                    infrastructure_component=infrastructure_component,
                    infrastructure_config=infrastructure_config,
                    distribution_config=distribution_config,
                    component_version=component_version,
                )
                pipelines.append(pipeline)
        return pipelines

    @staticmethod
    def _iter_vdi_configs(vdi_os_config: Dict[str, Any], target_region: str) -> Any:
        """Yield (os_name, arch, ami_config, arch_data) for each valid VDI AMI in the target region."""
        for os_name, os_data in vdi_os_config.items():
            for arch, arch_data in os_data.items():
                if target_region not in arch_data:
                    continue
                region_data = arch_data[target_region]
                if not isinstance(region_data, list) or len(region_data) == 0:
                    continue
                for ami_config in region_data:
                    if ami_config.get("ami-id"):
                        yield os_name, arch, ami_config, arch_data

    def _create_vdi_pipeline(
        self,
        os_name: str,
        arch: str,
        ami_config: Dict[str, Any],
        arch_data: Dict[str, Any],
        components: Dict[str, Any],
        infrastructure_config: Any,
        arm64_infrastructure_config: Any,
        distribution_config: Any,
        component_version: str,
    ) -> tuple[Any, Any]:
        """Create a single VDI image recipe + pipeline for one OS/arch combination."""
        ami_id = ami_config["ami-id"]
        platform = "Windows" if os_name == "windows" else "Linux"

        base_id = f"RESVDI{os_name.title()}{arch.replace('-', '').replace('_', '')}"

        # Build recipe components
        recipe_components = self._build_vdi_recipe_components(platform, components)

        image_recipe = imagebuilder.CfnImageRecipe(
            self,
            f"{base_id}ImageRecipe",
            name=f"res-vdi-{os_name}-{arch}-ami-recipe",
            version=component_version,
            parent_image=ami_id,
            description=f"Image recipe for RES VDI {os_name} {arch} AMI",
            components=recipe_components,
            block_device_mappings=_BLOCK_DEVICE_MAPPINGS,
        )

        # Select infrastructure config based on arch
        selected_infra_config = (
            arm64_infrastructure_config
            if "arm64" in arch.lower()
            else infrastructure_config
        )

        image_pipeline = imagebuilder.CfnImagePipeline(
            self,
            f"{base_id}ImagePipeline",
            name=f"res-vdi-{os_name}-{arch}-ami-pipeline",
            description=f"EC2 Image Builder pipeline for RES VDI {os_name} {arch} AMIs",
            image_recipe_arn=image_recipe.attr_arn,
            infrastructure_configuration_arn=selected_infra_config.attr_arn,
            distribution_configuration_arn=distribution_config.attr_arn,
            status="ENABLED",
            enhanced_image_metadata_enabled=True,
        )

        # Add dependencies
        component_key = "WindowsVDI" if platform == "Windows" else "LinuxVDI"
        image_recipe.add_dependency(components[component_key])
        image_pipeline.add_dependency(image_recipe)
        image_pipeline.add_dependency(selected_infra_config)
        image_pipeline.add_dependency(distribution_config)

        return image_recipe, image_pipeline

    def _build_vdi_recipe_components(
        self, platform: str, components: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build the Image Builder recipe component list for a VDI AMI."""
        if platform == "Linux":
            return [
                {
                    "componentArn": f"arn:{self.partition}:imagebuilder:{self.region}:aws:component/aws-cli-version-2-linux/x.x.x"
                },
                {
                    "componentArn": components["LinuxVDI"].attr_arn,
                    "parameters": [{"name": "GPUFamily", "value": ["NONE"]}],
                },
                {
                    "componentArn": f"arn:{self.partition}:imagebuilder:{self.region}:aws:component/simple-boot-test-linux/x.x.x"
                },
            ]
        else:
            return [
                {"componentArn": components["WindowsVDI"].attr_arn},
                {
                    "componentArn": f"arn:{self.partition}:imagebuilder:{self.region}:aws:component/simple-boot-test-windows/x.x.x"
                },
            ]

    # -------------------------------------------------------------------------
    # Infrastructure pipelines
    # -------------------------------------------------------------------------

    def _create_infra_pipeline(
        self,
        os_name: str,
        ami_id: str,
        infrastructure_component: Any,
        infrastructure_config: Any,
        distribution_config: Any,
        component_version: str,
    ) -> tuple[Any, Any]:
        """Create a single infrastructure image recipe + pipeline."""
        base_id = f"RESInfra{os_name.title()}"

        recipe_components = [
            {
                "componentArn": f"arn:{self.partition}:imagebuilder:{self.region}:aws:component/aws-cli-version-2-linux/x.x.x"
            },
            {
                "componentArn": f"arn:{self.partition}:imagebuilder:{self.region}:aws:component/amazon-cloudwatch-agent-linux/x.x.x"
            },
            {
                "componentArn": infrastructure_component.attr_arn,
                "parameters": [{"name": "AWSRegion", "value": [self.region]}],
            },
            {
                "componentArn": f"arn:{self.partition}:imagebuilder:{self.region}:aws:component/simple-boot-test-linux/x.x.x"
            },
        ]

        image_recipe = imagebuilder.CfnImageRecipe(
            self,
            f"{base_id}ImageRecipe",
            name=f"res-infra-{os_name}-ami-recipe",
            version=component_version,
            parent_image=ami_id,
            description=f"Image recipe for RES Infrastructure {os_name} AMI",
            components=recipe_components,
            block_device_mappings=_BLOCK_DEVICE_MAPPINGS,
            working_directory="/root/bootstrap/res-installation-scripts",
        )

        image_pipeline = imagebuilder.CfnImagePipeline(
            self,
            f"{base_id}ImagePipeline",
            name=f"res-infra-{os_name}-ami-pipeline",
            description=f"EC2 Image Builder pipeline for RES Infrastructure {os_name} AMIs",
            image_recipe_arn=image_recipe.attr_arn,
            infrastructure_configuration_arn=infrastructure_config.attr_arn,
            distribution_configuration_arn=distribution_config.attr_arn,
            status="ENABLED",
            enhanced_image_metadata_enabled=True,
        )

        # Add dependencies
        image_recipe.add_dependency(infrastructure_component)
        image_pipeline.add_dependency(image_recipe)
        image_pipeline.add_dependency(infrastructure_config)
        image_pipeline.add_dependency(distribution_config)

        return image_recipe, image_pipeline
