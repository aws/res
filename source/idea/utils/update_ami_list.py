#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
import argparse
import os.path
import sys

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


def main():
    parser = config_parser()
    args = parser.parse_args()
    global verbose
    verbose = args.verbose

    config_info = load_yaml(args.input_yaml_file)
    if args.type == "core":
        config_file = process_core_yaml(config_info)
        if args.output_file is not None:
            with open(args.output_file, "w") as file:
                yaml.dump(config_info, file, indent=2, default_flow_style=False)

    elif args.type == "vdi":
        print("VDI update has not been implemented yet")


if __name__ == "__main__":
    main()
