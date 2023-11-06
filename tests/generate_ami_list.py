import boto3
from dateutil.parser import parse
import yaml
from botocore.exceptions import ClientError


def get_all_regions():
    all_regions = []
    ec2 = boto3.client('ec2')
    try:
        for region in ec2.describe_regions(AllRegions=True)['Regions']:
            all_regions.append(region['RegionName'])
    except Exception as err:
        print("Error while trying to describe all regions due to {}".format(err))
    return all_regions


def get_image_by_region(distro, image_info, regions, architectures):
    arch_ami_list = {}
    for arch in architectures:
        ami_list = {}
        for region in regions:
            check_region = True
            if region in RESTRICTED_REGIONS["all"] or region in RESTRICTED_REGIONS[distro]:
                check_region = False
            if check_region is True:
                print("Checking {} ... ".format(region))
                ec2 = boto3.client('ec2', region_name=region)
                try:
                    distro_amis = ec2.describe_images(
                        ExecutableUsers=['all'],
                        Filters=[
                            {
                                'Name': 'name',
                                'Values': [
                                    image_info["name"],
                                ]
                            },
                            {
                                'Name': 'owner-id',
                                'Values': [
                                    image_info["owner_id"][region] if region in image_info["owner_id"].keys() else image_info["owner_id"][
                                        "default"]],

                            },

                            {
                                'Name': 'architecture',
                                'Values': [
                                    arch,
                                ]
                            },
                        ],
                    )
                except ClientError as err:
                    print(
                        'Unable to query this region. Most likely your IAM account is incorrect OR you have not opt-in on the region. Trace {} '.format(
                            err))
                    exit(1)

                if not distro_amis["Images"]:
                    print("Unable to retrieve AMI {} on {}".format(distro, region))
                    # exit(1)
                else:
                    for image in distro_amis["Images"]:
                        if region not in ami_list.keys():
                            ami_list[region] = {"ImageId": image["ImageId"], "CreationDate": parse(image["CreationDate"])}
                        else:
                            ami_date = parse(image["CreationDate"])
                            if ami_date > ami_list[region]["CreationDate"]:
                                ami_list[region] = {"ImageId": image["ImageId"], "CreationDate": parse(image["CreationDate"])}
        arch_ami_list[arch] = ami_list

    return arch_ami_list


if __name__ == "__main__":
    RESTRICTED_REGIONS = {"all": ["ap-northeast-3", "me-central-1"],  # Local Region
                          "amazonlinux2": [],
                          "centos7": ["ap-southeast-3"],
                          "rhel7": ["ap-southeast-3"],
                          "windows": []
                          }
    all_regions = get_all_regions()

    images_name = {
        "amazonlinux2": {
            "name": "amzn2-ami-hvm-2.0.*",
            "owner_id": {
                "default": "137112412989",
                "af-south-1": "210953353124",
                "me-south-1": "656109587541",
                "eu-south-1": "071630900071",
                "ap-east-1": "910595266909",
                "ap-southeast-3": "785737495101"
            }
        },
        "centos7": {"name": "CentOS 7*", "owner_id": {"default": "125523088429"}},
        "rhel7": {"name": "RHEL-7.9_HVM*", "owner_id": {"default": "309956199498"}},
        "windows": {"name": "DCV-Windows-2022.1.*", "owner_id": {"default": "877902723034"}}
    }

    image_display_map = {
        "amazonlinux2": "Amazon Linux 2",
        "centos7": "CentOS 7",
        "rhel7": "RHEL 7",
        "windows": "Windows",
    }

    DCV_WINDOWS_AMI = {
        "no": {
            "us-east-1": "ami-0a0c9ff5a39fda61f",
            "ca-central-1": "ami-016ca4a1fb96ec103",
            "us-east-2": "ami-0fa6df9543bc63b69",
            "us-west-1": "ami-0f260039dadd23aab",
            "us-west-2": "ami-0616f509f8c56edd3",
            "eu-west-1": "ami-01643440d0d3abc52",
            "eu-west-2": "ami-05a79fae5322ddf7b",
            "eu-west-3": "ami-09f72979d087b7ef8",
            "eu-central-1": "ami-004fd86583eb494ee",
            "eu-north-1": "ami-0db5739e8f768b605",
            "ap-northeast-1": "ami-03e9af94a9320bdf6",
            "ap-northeast-2": "ami-0348704713bf023f6",
            "ap-southeast-1": "ami-04a4a643aca2fb749",
            "ap-southeast-2": "ami-0c9120089f9f6eb5d",
            "ap-south-1": "ami-0307cbf9fc4c96c3e",
            "sa-east-1": "ami-082e6f2a2f1b98d29",
        },
        "amd": {
            'us-east-1': 'ami-09e9fc6b0563179e0',
            'ca-central-1': 'ami-02ce5abc7648ae028',
            'us-east-2': 'ami-0e9dffe211d55ea3d',
            'us-west-2': 'ami-0ca9facae744b755d',
            'eu-west-1': 'ami-0b79b4e3a40bdf60e',
            'eu-west-2': 'ami-049344b657f4fb45c',
            'eu-central-1': 'ami-01f877801cd06f23f',
            'ap-northeast-1': 'ami-0f73f5c42d0a2a659'
        },
        "nvidia": {
            'us-east-1': 'ami-0efdf76dd9f899c11',
            'ca-central-1': 'ami-024f599e25b98b213',
            'us-east-2': 'ami-0eb27d66bea34b823',
            'us-west-1': 'ami-0a44d985e3ccca06f',
            'us-west-2': 'ami-046766e4eef191f5c',
            'eu-west-1': 'ami-0bb7bad82b320fcca',
            'eu-west-2': 'ami-0be3d5c1d59782960',
            'eu-west-3': 'ami-0395cf74387ac6b14',
            'eu-central-1': 'ami-0649343058a73af62',
            'eu-north-1': 'ami-0745b0d998883f154',
            'ap-northeast-1': 'ami-0744247159c640e32',
            'ap-northeast-2': 'ami-0cc1538dd3712c9bc',
            'ap-southeast-1': 'ami-0e190f8939a996caf',
            'ap-southeast-2': 'ami-0e190f8939a996caf',
            'ap-south-1': 'ami-0bed7f8476b0a0f49',
            'sa-east-1': 'ami-0cce9af6bed94ceec'
        }
    }

    result = {}
    for distro, ami_name in images_name.items():
        print("Retrieving {} AMIs".format(distro))
        result[distro] = get_image_by_region(distro, ami_name, all_regions, ['x86_64', 'arm64'])

    yaml_data = {}
    for distro in images_name.keys():
        yaml_data[distro] = {}
        for arch in ['x86_64', 'arm64']:
            if len(result[distro][arch]) == 0:
                continue

            arch_yaml = arch
            if arch == 'x86_64':
                arch_yaml = 'x86-64'

            yaml_data[distro][arch_yaml] = {
                "default-name": image_display_map[distro],
                "default-description": image_display_map[distro],
                "default-min-storage-value": 10,
                "default-min-storage-unit": "gb",
                "default-min-ram-value": 4,
                "default-min-ram-unit": "gb"
            }

            if distro == 'windows':
                yaml_data[distro][arch_yaml]["default-min-storage-value"] = 30

            for region in all_regions:
                if region in result[distro][arch].keys():
                    yaml_data[distro][arch_yaml][region] = [{
                        "ami-id": result[distro][arch][region]["ImageId"],
                        "ss-id-suffix": "base"
                    }]

    for gpu in ["no", "amd", "nvidia"]:
        for region in DCV_WINDOWS_AMI[gpu].keys():
            if region in yaml_data['windows']['x86-64'].keys():
                # region found, it already has default
                if gpu != 'no':
                    yaml_data['windows']['x86-64'][region].append({
                        "ami-id": DCV_WINDOWS_AMI[gpu][region],
                        "ss-id-suffix": "base-" + gpu,
                        "name": "Windows - " + gpu.upper(),
                        "description": "Windows - " + gpu.upper(),
                        "gpu-manufacturer": gpu.upper()
                    })
            else:
                yaml_data['windows']['x86-64'][region] = []
                if gpu != 'no':
                    yaml_data['windows']['x86-64'][region].append({
                        "ami-id": DCV_WINDOWS_AMI[gpu][region],
                        "ss-id-suffix": "base-" + gpu,
                        "name": "Windows - " + gpu.upper(),
                        "description": "Windows - " + gpu.upper(),
                        "gpu-manufacturer": gpu.upper()
                    })
                else:
                    yaml_data['windows']['x86-64'][region].append({
                        "ami-id": DCV_WINDOWS_AMI[gpu][region],
                        "ss-id-suffix": "base",
                        "name": "Windows",
                        "description": "Windows",
                    })

    print(yaml.dump(yaml_data))
