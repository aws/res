#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import pytest
from unittest.mock import patch, MagicMock
import subprocess
from unittest.mock import mock_open
from ideabootstrap.bootstrap_common import (
    disable_ulimit
)
from ideabootstrap.common import (
    network_interface_tags,
    ebs_volume_tags,
    chronyd,
    idea_service_account,
)
from ideabootstrap.common.chronyd import chrony_conf

@pytest.fixture
def mock_instance_id():
    return "i-1234567890abcdef0"

@pytest.fixture
def mock_volumes_output():
    return "vol-1234567890abcdef0\nvol-0987654321fedcba0"

def test_set_ebs_volume_tags_success(monkeypatch, mock_instance_id, mock_volumes_output):
    env_vars = {
        "IDEA_CLUSTER_NAME": "test-cluster",
        "IDEA_MODULE_NAME": "test-module",
        "IDEA_MODULE_ID": "test-id",
        "AWS_REGION": "us-west-2"
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    mock_ec2_client = MagicMock()
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_ec2_client

    mock_ec2_client.describe_volumes.return_value = {
        'Volumes': [
            {'VolumeId': 'vol-1234567890abcdef0'},
            {'VolumeId': 'vol-0987654321fedcba0'}
        ]
    }

    with patch('res.utils.instance_metadata_utils.get_instance_id', return_value=mock_instance_id), \
         patch('boto3.client', mock_boto3.client), \
         patch('res.resources.cluster_settings.get_setting', return_value=["Key=test-key,Value=test-value"]):    

        ebs_volume_tags.setup()

        # Verify boto3 client was created with correct parameters
        mock_boto3.client.assert_called_once_with('ec2', region_name=env_vars["AWS_REGION"])

        # Verify describe_volumes was called with correct parameters
        mock_ec2_client.describe_volumes.assert_called_once_with(
            Filters=[
                {
                    'Name': 'attachment.instance-id',
                    'Values': [mock_instance_id]
                }
            ]
        )

        expected_tags = [
            {'Key': 'res:EnvironmentName', 'Value': env_vars["IDEA_CLUSTER_NAME"]},
            {'Key': 'res:ModuleName', 'Value': env_vars["IDEA_MODULE_NAME"]},
            {'Key': 'res:ModuleId', 'Value': env_vars["IDEA_MODULE_ID"]},
            {'Key': 'Name', 'Value': env_vars["IDEA_CLUSTER_NAME"] + '/' + env_vars["IDEA_MODULE_ID"] + ' Root Volume'},
            {'Key': 'test-key', 'Value': 'test-value'}
        ]

        assert mock_ec2_client.create_tags.call_count == 2

        mock_ec2_client.create_tags.assert_any_call(
            Resources=['vol-1234567890abcdef0'],
            Tags=expected_tags
        )

        mock_ec2_client.create_tags.assert_any_call(
            Resources=['vol-0987654321fedcba0'],
            Tags=expected_tags
        )

@pytest.fixture
def mock_interfaces_output():
    return "eni-1234567890abcdef0\neni-0987654321fedcba0"

def test_set_network_interface_tags_success(monkeypatch, mock_instance_id, mock_interfaces_output):
    env_vars = {
        "IDEA_CLUSTER_NAME": "test-cluster",
        "IDEA_MODULE_NAME": "test-module",
        "IDEA_MODULE_ID": "test-id",
        "AWS_REGION": "us-west-2"
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    # Mock the boto3 clients and their methods
    mock_ec2_client = MagicMock()

    # Mock the describe_network_interfaces response
    mock_ec2_client.describe_network_interfaces.return_value = {
        'NetworkInterfaces': [
            {'NetworkInterfaceId': 'eni-1234567890abcdef0'},
            {'NetworkInterfaceId': 'eni-0987654321fedcba0'}
        ]
    }

    mock_ec2_client.create_tags.return_value = {'Return': True}

    with patch('boto3.client', return_value=mock_ec2_client), \
         patch('res.utils.instance_metadata_utils.get_instance_id', return_value=mock_instance_id), \
         patch('res.resources.cluster_settings.get_setting', return_value=["Key=test-key,Value=test-value"]):    

        ebs_volume_tags.setup()

        result = network_interface_tags.setup()

        mock_ec2_client.describe_network_interfaces.assert_called_once_with(
            Filters=[{'Name': 'attachment.instance-id', 'Values': [mock_instance_id]}]
        )

        expected_tags = [
            {'Key': 'res:EnvironmentName', 'Value': env_vars["IDEA_CLUSTER_NAME"]},
            {'Key': 'res:ModuleName', 'Value': env_vars["IDEA_MODULE_NAME"]},
            {'Key': 'res:ModuleId', 'Value': env_vars["IDEA_MODULE_ID"]},
            {'Key': 'Name', 'Value': env_vars["IDEA_CLUSTER_NAME"] + '/' + env_vars["IDEA_MODULE_ID"] + '  Network Interface'},
            {'Key': 'test-key', 'Value': 'test-value'}
        ]

        assert mock_ec2_client.create_tags.call_count == 2

        mock_ec2_client.create_tags.assert_any_call(
            Resources=['eni-1234567890abcdef0'],
            Tags=expected_tags
        )

        mock_ec2_client.create_tags.assert_any_call(
            Resources=['eni-0987654321fedcba0'],
            Tags=expected_tags
        )


@pytest.fixture
def mock_instance_id():
    return "i-1234567890abcdef0"

@pytest.fixture
def mock_cloudwatch_classes():
    mock_log_file_options = MagicMock()
    mock_cloudwatch_agent_config = MagicMock()
    mock_cluster_config = MagicMock()
    mock_config_options = MagicMock()
    mock_logs_options = MagicMock()

    mock_cloudwatch_agent_config.return_value.build.return_value = {
        "agent": {"region": "us-west-2"},
        "logs": {"logs_collected": {"files": {"collect_list": []}}}
    }

    return {
        "CloudWatchAgentLogFileOptions": mock_log_file_options,
        "CloudWatchAgentConfig": mock_cloudwatch_agent_config,
        "ClusterConfig": mock_cluster_config,
        "CloudWatchAgentConfigOptions": mock_config_options,
        "CloudWatchAgentLogsOptions": mock_logs_options
    }

def test_configure_chronyd_rhel8(monkeypatch):
    """Test configure_chronyd function for RHEL 8."""

    mock_get_base_os = MagicMock(return_value="rhel8")
    mock_path_exists = MagicMock(return_value=True)
    mock_shutil_move = MagicMock()
    mock_subprocess_run = MagicMock()
    mock_file = mock_open()
    mock_logger = MagicMock()

    # Patch the functions where they are imported in chronyd.py
    with patch('ideabootstrap.common.chronyd.get_base_os', mock_get_base_os), \
         patch('ideabootstrap.common.chronyd.os.path.exists', mock_path_exists), \
         patch('ideabootstrap.common.chronyd.shutil.move', mock_shutil_move), \
         patch('ideabootstrap.common.chronyd.subprocess.run', mock_subprocess_run), \
         patch('ideabootstrap.common.chronyd.open', mock_file, create=True), \
         patch('ideabootstrap.common.chronyd.logger', mock_logger):

        chronyd.configure()
        mock_get_base_os.assert_called_once()
        mock_path_exists.assert_called_once_with('/etc/chrony.conf')
        mock_shutil_move.assert_called_once_with('/etc/chrony.conf', '/etc/chrony.conf.original')

        assert mock_subprocess_run.call_count == 2
        mock_subprocess_run.assert_any_call(['yum', 'remove', '-y', 'ntp'], check=True)
        mock_subprocess_run.assert_any_call(['systemctl', 'enable', 'chronyd'], check=True)

        mock_file.assert_called_once_with('/etc/chrony.conf', 'w')

        file_handle = mock_file()
        file_handle.write.assert_called_once_with(chrony_conf)

        mock_logger.info.assert_any_call("Chronyd configuration completed successfully")

        mock_logger.error.assert_not_called()

def test_create_idea_service_account_create_success(monkeypatch):
    """Test create_idea_service_account when the account needs to be created."""
    def side_effect_function(*args, **kwargs):
        if args[0][0] == "id":
            raise subprocess.CalledProcessError(1, args[0])
        else:
            return MagicMock(returncode=0)

    mock_subprocess_run = MagicMock(side_effect=side_effect_function)
    mock_logger = MagicMock()

    with patch('subprocess.run', mock_subprocess_run), \
        patch('ideabootstrap.common.idea_service_account.logger', mock_logger):

        idea_service_account.setup_account()

        assert mock_subprocess_run.call_count == 2

        mock_subprocess_run.assert_any_call(
            ["id", "ideaserviceaccount"],
            check=True,
            stdout=-1,
            stderr=-1
        )

        mock_subprocess_run.assert_any_call(
            ["useradd", "--system", "--shell", "/bin/false", "ideaserviceaccount"],
            check=True
        )

        mock_logger.info.assert_any_call("Successfully created ideaserviceaccount")

def test_disable_ulimit_supported_os():
    mock_get_base_os = MagicMock(return_value="rhel8")

    mock_file = mock_open()

    mock_logger = MagicMock()

    with patch('ideabootstrap.bootstrap_common.get_base_os', mock_get_base_os), \
        patch('builtins.open', mock_file), \
        patch('ideabootstrap.bootstrap_common.logger', mock_logger):

        disable_ulimit()

        mock_get_base_os.assert_called_once()

        mock_file.assert_called_once_with('/etc/security/limits.conf', 'a')

        file_handle = mock_file()
        file_handle.write.assert_any_call("\n")
        file_handle.write.assert_any_call("* hard memlock unlimited\n")
        file_handle.write.assert_any_call("* soft memlock unlimited\n")

        mock_logger.info.assert_any_call("Successfully updated /etc/security/limits.conf with unlimited memlock settings")

        mock_logger.error.assert_not_called()
