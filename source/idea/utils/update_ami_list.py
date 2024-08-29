#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import argparse
import os.path
import sys
from datetime import datetime

import boto3
import yaml

# This is a simple util to provide a quick mechanism to get the new AMI ids.
# As of now it supports the infrastructure AMIs.
# Need to determine method to support updating VDI ami-ids.

verbose = False


def config_parser():
    parser = argparse.ArgumentParser(
        prog="update_ami_list",
        description="Updates ami list to latest revision of same version",
        epilog="",
    )
    parser.add_argument("input_yaml_file")
    parser.add_argument("-t", "--type", choices=["core", "vdi"], required=True)
    parser.add_argument("-o", "--output_file")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument(
        "-r",
        "--region",
        help="Pass 'all_classic' to update ami list for all AWS classic regions",
    )
    return parser


def load_yaml(yaml_file):
    if not os.path.isfile(yaml_file):
        sys.exit("Input file did not exist")
    with open(yaml_file, "r") as file:
        data = yaml.safe_load(file)
    return data


def process_core_yaml(config_info):
    for region in config_info:
        try:
            ssm_client = boto3.client("ssm", region_name=region)
            if verbose:
                print(f"The region is {region}")
            for ami_item in config_info[region]:
                response = ssm_client.get_parameters(
                    Names=[
                        "/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2",
                    ],
                    WithDecryption=True | False,
                )
                ami_id = response["Parameters"][0]["Value"]
                config_info[region][ami_item] = ami_id
        except:
            print(f"Could not get image data for {region} region.")

    if verbose:
        print(yaml.dump(config_info, indent=2, default_flow_style=False))


def get_latest_ami_id_by_ami_name(ec2_client, ami_name):
    response = ec2_client.describe_images(
        Filters=[
            {"Name": "name", "Values": [ami_name]},
        ],
        IncludeDeprecated=True,
    )
    images = sorted(
        response.get("Images", []),
        key=lambda image: datetime.strptime(
            image["CreationDate"], "%Y-%m-%dT%H:%M:%S.%fZ"
        ),
        reverse=True,
    )

    image_id = images[0].get("ImageId", "") if len(images) > 0 else ""
    if not image_id:
        print(f"Could not get the latest AMI ID with name {ami_name}")
    return image_id


def add_or_update_ami_info(
    ami_info_list,
    region,
    ami_id,
    ss_id_suffix,
    description=None,
    gpu_manufacturer=None,
    name=None,
):
    if not ami_id:
        return

    if not ami_info_list.get(region):
        ami_info_list[region] = []

    ami_info_exists = False
    for ami_info in ami_info_list[region]:
        if ami_info.get("ss-id-suffix", "") == ss_id_suffix:
            ami_info_exists = True

            ami_info["ami-id"] = ami_id
            if description:
                ami_info["description"] = description
            if gpu_manufacturer:
                ami_info["gpu-manufacturer"] = gpu_manufacturer
            if name:
                ami_info["name"] = name
            break

    if not ami_info_exists:
        ami_info = {"ami-id": ami_id, "ss-id-suffix": ss_id_suffix}
        if description:
            ami_info["description"] = description
        if gpu_manufacturer:
            ami_info["gpu-manufacturer"] = gpu_manufacturer
        if name:
            ami_info["name"] = name

        ami_info_list[region].append(ami_info)


def process_vdi_yaml(config_info, region):
    ssm_client = boto3.client("ssm", region_name=region)
    ec2_client = boto3.client("ec2", region_name=region)

    for platform in config_info.keys():
        if platform == "amazonlinux2":
            # Query for the latest Amazon Linux AMI IDs using AWS Systems Manager Parameter Store
            # https://aws.amazon.com/blogs/compute/query-for-the-latest-amazon-linux-ami-ids-using-aws-systems-manager-parameter-store/
            for arch in config_info[platform].keys():
                arch_identifier = arch.replace("-", "_")
                response = ssm_client.get_parameters(
                    Names=[
                        f"/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-{arch_identifier}-gp2",
                    ],
                    WithDecryption=True | False,
                )
                if len(response.get("Parameters", [])) > 0:
                    base_ami_id = response["Parameters"][0].get("Value", "")
                    add_or_update_ami_info(
                        config_info[platform][arch], region, base_ami_id, "base"
                    )
                else:
                    print(
                        f"Could not get the latest AMI ID for {platform} {arch} from SSM public parameters"
                    )

        elif platform in ["rhel8", "rhel9"]:
            # Only x86-64 architecture is supported currently.
            rhel_version = platform.replace("rhel", "")
            base_ami_id = get_latest_ami_id_by_ami_name(
                ec2_client, f"RHEL-{rhel_version}.*_HVM-*-x86_64-*-Hourly2-GP2"
            )
            add_or_update_ami_info(
                config_info[platform]["x86-64"], region, base_ami_id, "base"
            )

        elif platform == "windows":
            # Only x86-64 architecture is supported currently.
            base_ami_id = get_latest_ami_id_by_ami_name(
                ec2_client, f"DCV-Windows-2023.*-DOD-*"
            )
            add_or_update_ami_info(
                config_info[platform]["x86-64"], region, base_ami_id, "base"
            )

            amd_ami_id = get_latest_ami_id_by_ami_name(
                ec2_client, f"DCV-Windows-2023.*-AMD-*"
            )
            add_or_update_ami_info(
                config_info[platform]["x86-64"],
                region,
                amd_ami_id,
                "base-amd",
                "Windows - AMD",
                "AMD",
                "Windows - AMD",
            )

            nvidia_ami_id = get_latest_ami_id_by_ami_name(
                ec2_client, f"DCV-Windows-2023.*-NVIDIA-*"
            )
            add_or_update_ami_info(
                config_info[platform]["x86-64"],
                region,
                nvidia_ami_id,
                "base-nvidia",
                "Windows - NVIDIA",
                "NVIDIA",
                "Windows - NVIDIA",
            )

        elif platform == "ubuntu2204":
            # Only x86-64 architecture is supported currently.
            base_ami_id = get_latest_ami_id_by_ami_name(
                ec2_client,
                f"ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20240125",
            )

            add_or_update_ami_info(
                config_info[platform]["x86-64"], region, base_ami_id, "base"
            )


def main():
    parser = config_parser()
    args = parser.parse_args()
    global verbose
    verbose = args.verbose

    all_supported_classic_regions = [
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-south-1",
        "ap-southeast-1",
        "ap-southeast-2",
        "ca-central-1",
        "eu-central-1",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
    ]

    # This list is informational. For updating AMIs in opt-in regions or gov cloud the account whose credentials are assumed must have the region enabled.
    # all_supported_opt_in_regions = ["eu-south-1", "il-central-1"]
    # all_supported_gov_cloud_regions = ["us-gov-west-1"]

    config_info = load_yaml(args.input_yaml_file)
    if args.type == "core":
        process_core_yaml(config_info)
        if args.output_file is not None:
            with open(args.output_file, "w") as file:
                yaml.dump(config_info, file, indent=2, default_flow_style=False)

    elif args.type == "vdi":
        if not args.region:
            raise "Region is required for updating VDI AMIs"

        regions = (
            all_supported_classic_regions
            if args.region == "all_classic"
            else [args.region]
        )

        for region in regions:
            print(f"Processing region: {region}")
            process_vdi_yaml(config_info, region)

        if args.output_file is not None:
            with open(args.output_file, "w") as file:
                yaml.dump(config_info, file, indent=2, default_flow_style=False)


if __name__ == "__main__":
    main()
