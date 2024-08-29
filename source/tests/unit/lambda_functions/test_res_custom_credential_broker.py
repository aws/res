import json
from unittest.mock import MagicMock, patch

from lambda_functions.res_custom_credential_broker.utils import Utils


def test_get_instance_id_from_user_arn():
    user_arn = "arn:aws:sts::123456789012:assumed-role/MyRole/i-1234567890abcdef0"
    instance_id = Utils.get_instance_id_from_user_arn(user_arn)
    assert instance_id == "i-1234567890abcdef0"


def test_get_instance_id_from_user_arn_no_match():
    user_arn = "arn:aws:sts::123456789012:assumed-role/MyRole"
    instance_id = Utils.get_instance_id_from_user_arn(user_arn)
    assert instance_id is None


def test_get_source_ip_from_request_context():
    request_context = {"identity": {"sourceIp": "192.168.1.1"}}
    source_ip = Utils.get_source_ip_from_request_context(request_context)
    assert source_ip == "192.168.1.1"


def test_get_filesystem_name_from_request_context():
    event = {"queryStringParameters": {"filesystemName": "myfilesystem"}}
    filesystem_name = Utils.get_filesystem_name_from_request_context(event)
    assert filesystem_name == "myfilesystem"


@patch("boto3.client")
def test_validate_instance_origin(mock_boto_client):
    ec2_client = MagicMock()
    ec2_client.describe_instances.return_value = {
        "Reservations": [{"Instances": [{"PrivateIpAddress": "192.168.1.1"}]}]
    }
    mock_boto_client.return_value = ec2_client

    is_valid = Utils.validate_instance_origin("i-1234567890abcdef0", "192.168.1.1")
    assert is_valid is True


@patch("boto3.client")
def test_validate_instance_origin_with_invalid_origin(mock_boto_client):
    ec2_client = MagicMock()
    ec2_client.describe_instances.return_value = {
        "Reservations": [{"Instances": [{"PrivateIpAddress": "192.168.1.1"}]}]
    }
    mock_boto_client.return_value = ec2_client

    is_valid = Utils.validate_instance_origin("i-1234567890abcdef0", "192.168.1.5")
    assert is_valid is False


@patch("boto3.client")
def test_get_temporary_credentials(mock_boto_client):
    sts_client = MagicMock()
    sts_client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "AKIA...",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
            "Expiration": MagicMock(
                isoformat=MagicMock(return_value="2023-01-01T00:00:00")
            ),
        }
    }
    mock_boto_client.return_value = sts_client

    credentials = Utils.get_temporary_credentials(
        "role_arn", "session_name", True, "bucket_arn"
    )
    assert credentials["AccessKeyId"] == "AKIA..."
    assert credentials["SecretAccessKey"] == "secret"
    assert credentials["SessionToken"] == "token"
    assert credentials["Expiration"] == "2023-01-01T00:00:00"


def test_extract_bucket_arn_without_prefix():
    bucket_arn = "arn:aws:s3:::mybucket"
    result = Utils.extract_bucket_arn_without_prefix(bucket_arn)
    assert result == "arn:aws:s3:::mybucket"


def test_extract_prefix_from_bucket_arn():
    bucket_arn = "arn:aws:s3:::mybucket/myprefix"
    prefix = Utils.extract_prefix_from_bucket_arn(bucket_arn)
    assert prefix == "myprefix"


def test_extract_prefix_from_bucket_arn_no_prefix():
    bucket_arn = "arn:aws:s3:::mybucket"
    prefix = Utils.extract_prefix_from_bucket_arn(bucket_arn)
    assert prefix is None


def test_generate_session_policy_read_only_with_prefix():
    bucket_arn = "arn:aws:s3:::mybucket"
    prefix = "myprefix"
    policy = Utils.generate_session_policy(True, bucket_arn, prefix)
    policy_dict = json.loads(policy)

    expected_actions = ["s3:GetObject"]
    expected_list_action = ["s3:ListBucket"]
    expected_resource = f"{bucket_arn}/{prefix}/*"
    expected_condition = {"StringLike": {"s3:prefix": f"{prefix}/*"}}
    statement = policy_dict["Statement"]
    assert statement[0]["Action"] == expected_actions
    assert statement[0]["Resource"] == expected_resource
    assert statement[1]["Action"] == expected_list_action
    assert statement[1]["Condition"] == expected_condition


def test_generate_session_policy_read_write_with_prefix():
    bucket_arn = "arn:aws:s3:::mybucket"
    prefix = "myprefix"
    policy = Utils.generate_session_policy(False, bucket_arn, prefix)
    policy_dict = json.loads(policy)

    expected_actions = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:DeleteObject",
    ]
    expected_list_action = ["s3:ListBucket"]
    expected_resource = f"{bucket_arn}/{prefix}/*"
    expected_condition = {"StringLike": {"s3:prefix": f"{prefix}/*"}}

    statement = policy_dict["Statement"]
    assert statement[0]["Action"] == expected_actions
    assert statement[0]["Resource"] == expected_resource
    assert statement[1]["Action"] == expected_list_action
    assert statement[1]["Condition"] == expected_condition


def test_generate_session_policy_read_only_no_prefix():
    bucket_arn = "arn:aws:s3:::mybucket"
    policy = Utils.generate_session_policy(True, bucket_arn)
    policy_dict = json.loads(policy)

    expected_actions = ["s3:ListBucket", "s3:GetObject"]
    expected_resources = [f"{bucket_arn}/*", bucket_arn]

    statement = policy_dict["Statement"]
    assert statement[0]["Action"] == expected_actions
    assert statement[0]["Resource"] == expected_resources


def test_generate_session_policy_read_only_with_empty_prefix():
    bucket_arn = "arn:aws:s3:::mybucket"
    prefix = ""
    policy = Utils.generate_session_policy(True, bucket_arn, prefix)
    policy_dict = json.loads(policy)

    expected_actions = ["s3:ListBucket", "s3:GetObject"]
    expected_resources = [f"{bucket_arn}/*", bucket_arn]

    statement = policy_dict["Statement"]
    assert statement[0]["Action"] == expected_actions
    assert statement[0]["Resource"] == expected_resources


def test_generate_session_policy_read_write_with_empty_prefix():
    bucket_arn = "arn:aws:s3:::mybucket"
    prefix = ""
    policy = Utils.generate_session_policy(False, bucket_arn, prefix)
    policy_dict = json.loads(policy)

    expected_actions = [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:DeleteObject",
    ]
    expected_resources = [f"{bucket_arn}/*", bucket_arn]

    statement = policy_dict["Statement"]
    assert statement[0]["Action"] == expected_actions
    assert statement[0]["Resource"] == expected_resources


def test_generate_session_policy_read_write_no_prefix():
    bucket_arn = "arn:aws:s3:::mybucket"
    policy = Utils.generate_session_policy(False, bucket_arn)
    policy_dict = json.loads(policy)

    expected_actions = [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject",
        "s3:AbortMultipartUpload",
        "s3:DeleteObject",
    ]
    expected_resources = [f"{bucket_arn}/*", bucket_arn]

    statement = policy_dict["Statement"]
    assert statement[0]["Action"] == expected_actions
    assert statement[0]["Resource"] == expected_resources
