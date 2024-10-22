from unittest.mock import MagicMock

import pytest
from ideasdk.context import BootstrapContext

from ideadatamodel import constants, errorcodes, exceptions


def set_up_context():
    # Mock configuration and utility classes
    mock_config = MagicMock()

    # Mock SocaAnyPayload class with project and session_owner variables
    mock_vars = MagicMock()
    mock_vars.project = "test_project"
    mock_vars.session_owner = "test_owner"

    # Initialize BootstrapContext
    context = BootstrapContext(
        config=mock_config,
        module_name="test_module",
        module_id="test_module_id",
        base_os="amazonlinux2",
        instance_type="t2.micro",
        module_set="test_module_set",
    )
    context.vars = mock_vars

    return context


def test_get_prefix_for_object_storage_read_only_with_no_match():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name"
    read_only = True
    result = context.get_prefix_for_object_storage(bucket_arn, read_only)
    assert result == ""


def test_get_prefix_for_object_storage_read_only_with_match():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name/some/prefix"
    read_only = True
    result = context.get_prefix_for_object_storage(bucket_arn, read_only)
    assert result == "some/prefix/"


def test_get_prefix_for_object_storage_read_only_with_match_and_trailing_slash():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name/some/prefix/"
    read_only = True
    result = context.get_prefix_for_object_storage(bucket_arn, read_only)
    assert result == "some/prefix/"


def test_get_prefix_for_object_storage_read_write_with_custom_prefix_project_and_user_with_root_bucket_arn():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name"
    read_only = False
    custom_prefix = constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX
    result = context.get_prefix_for_object_storage(bucket_arn, read_only, custom_prefix)
    assert result == "test_project/test_owner/"


def test_get_prefix_for_object_storage_read_write_with_custom_prefix_project_and_user():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name/some/prefix"
    read_only = False
    custom_prefix = constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX
    result = context.get_prefix_for_object_storage(bucket_arn, read_only, custom_prefix)
    assert result == "some/prefix/test_project/test_owner/"


def test_get_prefix_for_object_storage_read_write_with_custom_prefix_project_and_user_trailing_slash():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name/some/prefix/"
    read_only = False
    custom_prefix = constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_AND_USERNAME_PREFIX
    result = context.get_prefix_for_object_storage(bucket_arn, read_only, custom_prefix)
    assert result == "some/prefix/test_project/test_owner/"


def test_get_prefix_for_object_storage_read_write_with_custom_prefix_project_with_root_bucket_arn():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name"
    read_only = False
    custom_prefix = constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX
    result = context.get_prefix_for_object_storage(bucket_arn, read_only, custom_prefix)
    assert result == "test_project/"


def test_get_prefix_for_object_storage_read_write_with_custom_prefix_project():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name/some/prefix"
    read_only = False
    custom_prefix = constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX
    result = context.get_prefix_for_object_storage(bucket_arn, read_only, custom_prefix)
    assert result == "some/prefix/test_project/"


def test_get_prefix_for_object_storage_read_write_with_custom_prefix_project_trailing_slash():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name/some/prefix/"
    read_only = False
    custom_prefix = constants.OBJECT_STORAGE_CUSTOM_PROJECT_NAME_PREFIX
    result = context.get_prefix_for_object_storage(bucket_arn, read_only, custom_prefix)
    assert result == "some/prefix/test_project/"


def test_get_prefix_for_object_storage_read_write_with_no_custom_prefix_with_root_bucket_arn():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name"
    read_only = False
    custom_prefix = constants.OBJECT_STORAGE_NO_CUSTOM_PREFIX
    result = context.get_prefix_for_object_storage(bucket_arn, read_only, custom_prefix)
    assert result == ""


def test_get_prefix_for_object_storage_read_write_with_no_custom_prefix():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name/some/prefix"
    read_only = False
    custom_prefix = constants.OBJECT_STORAGE_NO_CUSTOM_PREFIX
    result = context.get_prefix_for_object_storage(bucket_arn, read_only, custom_prefix)
    assert result == "some/prefix/"


def test_get_prefix_for_object_storage_read_write_with_no_custom_prefix_trailing_slash():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name/some/prefix/"
    read_only = False
    custom_prefix = constants.OBJECT_STORAGE_NO_CUSTOM_PREFIX
    result = context.get_prefix_for_object_storage(bucket_arn, read_only, custom_prefix)
    assert result == "some/prefix/"


def test_get_prefix_for_object_storage_read_write_without_custom_prefix_raises_error():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name/some/prefix"
    read_only = False
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.get_prefix_for_object_storage(bucket_arn, read_only)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert (
        "custom_bucket_prefix is required for read/write object storage"
        in exc_info.value.message
    )


def test_get_prefix_for_object_storage_read_write_with_invalid_custom_prefix_raises_error():
    context = set_up_context()
    bucket_arn = "arn:aws:s3:::bucket-name/some/prefix"
    read_only = False
    custom_prefix = "INVALID_PREFIX"
    with pytest.raises(exceptions.SocaException) as exc_info:
        context.get_prefix_for_object_storage(bucket_arn, read_only, custom_prefix)
    assert exc_info.value.error_code == errorcodes.INVALID_PARAMS
    assert "invalid custom_prefix" in exc_info.value.message
