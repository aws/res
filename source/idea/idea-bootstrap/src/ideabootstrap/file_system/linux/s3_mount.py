#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import re
import shutil
import subprocess

import ideabootstrap.file_system.linux.constants as constants


def get_bucket_name(bucket_arn: str) -> str:
    bucket_arn_regex = re.compile(constants.S3_BUCKET_ARN_REGEX)
    match = bucket_arn_regex.match(bucket_arn)
    if match:
        return match.group(1)
    return ""


def get_prefix_for_object_storage(
    bucket_arn: str, read_only: bool, custom_prefix: str = None
) -> str:
    match = re.match(constants.S3_BUCKET_ARN_PREFIX_REGEX, bucket_arn)
    prefix = ""
    if match:
        prefix = match.group(1).rstrip("/")
    if not read_only:
        if custom_prefix:
            if (
                custom_prefix
                == constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX
            ):
                prefix = f'/{prefix}/{os.environ.get("PROJECT_NAME")}/{os.environ.get("IDEA_SESSION_OWNER")}/'
            elif custom_prefix == constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX:
                prefix = f'/{prefix}/{os.environ.get("PROJECT_NAME")}/'
            elif custom_prefix == constants.OBJECT_STORAGE_NO_CUSTOM_PREFIX:
                pass
            else:
                raise Exception("invalid custom_prefix")
        else:
            raise Exception(
                "custom_bucket_prefix is required for read/write object storage"
            )
    if prefix:
        prefix = f"{prefix.lstrip('/').rstrip('/')}/"
    return prefix


def _configure_aws_credentials(
    custom_credential_broker_script_location: str, fs_name: str, api_url: str
) -> None:
    profile_name = f"{fs_name}-profile"
    aws_default_region = os.environ.get("AWS_DEFAULT_REGION")

    aws_commands = [
        ["aws", "configure", "set", "output", "json"],
        ["aws", "configure", "set", "region", aws_default_region],
        [
            "aws",
            "configure",
            "set",
            "credential_process",
            f"idea_python {custom_credential_broker_script_location} --filesystem-name {fs_name} --api-url {api_url}",
            "--profile",
            profile_name,
        ],
        ["aws", "configure", "set", "output", "json", "--profile", profile_name],
        [
            "aws",
            "configure",
            "set",
            "region",
            aws_default_region,
            "--profile",
            profile_name,
        ],
    ]

    for cmd in aws_commands:
        subprocess.run(cmd, check=True)


def add_s3_bucket(
    custom_credential_broker_script_location: str,
    api_url: str,
    fs_name: str,
    mount_dir: str,
    bucket_name: str,
    read_only: bool = True,
    prefix: str = None,
):
    profile_name = f"{fs_name}-profile"
    mount_s3 = shutil.which("mount-s3")

    _configure_aws_credentials(
        custom_credential_broker_script_location, fs_name, api_url
    )

    mount_command = [mount_s3, bucket_name, mount_dir, "--allow-other"]

    if read_only:
        mount_command.append("--read-only")
    else:
        mount_command.extend(
            [
                "--allow-delete",
                "--allow-overwrite",
                "--dir-mode",
                "0777",
                "--file-mode",
                "0777",
            ]
        )

    if prefix:
        mount_command.extend(["--prefix", prefix])

    # Execute mount command
    env = os.environ.copy()
    env["AWS_PROFILE"] = profile_name
    subprocess.run(mount_command, env=env, check=True)

    # Create systemd service
    service_name = f"{fs_name}-mount-s3"
    service_file = os.path.join(
        constants.SYSTEMD_SERVICE_FILE_DIR, f"{service_name}.service"
    )

    service_content = f"""[Unit]
Description=Mountpoint for Amazon S3 mount
Wants=network.target
AssertPathIsDirectory={mount_dir}

[Service]
Type=forking
User=root
ExecStart=/bin/bash -c 'AWS_PROFILE={profile_name} {" ".join(mount_command)}'
ExecStop=/usr/bin/fusermount -u {mount_dir}
Restart=always

[Install]
WantedBy=remote-fs.target
"""

    with open(service_file, "w") as f:
        f.write(service_content)

    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", f"{service_name}.service"], check=True)
