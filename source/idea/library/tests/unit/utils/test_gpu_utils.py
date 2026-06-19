#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

from res.utils import gpu_utils


@patch("res.utils.gpu_utils.cluster_settings.get_setting")
def test_is_gpu_instance_type_true(mock_get_setting):
    mock_get_setting.return_value = ["p3", "g4dn", "g5"]
    assert gpu_utils.is_gpu_instance_type("p3.2xlarge") is True


@patch("res.utils.gpu_utils.cluster_settings.get_setting")
def test_is_gpu_instance_type_false(mock_get_setting):
    mock_get_setting.return_value = ["p3", "g4dn", "g5"]
    assert gpu_utils.is_gpu_instance_type("t3.medium") is False


@patch("res.utils.gpu_utils.cluster_settings.get_setting")
def test_is_nvidia_gpu_true(mock_get_setting):
    mock_get_setting.return_value = "535.129.03"
    assert gpu_utils.is_nvidia_gpu("p3.2xlarge") is True


@patch("res.utils.gpu_utils.cluster_settings.get_setting")
def test_is_nvidia_gpu_false(mock_get_setting):
    mock_get_setting.side_effect = Exception("not found")
    assert gpu_utils.is_nvidia_gpu("t3.medium") is False


@patch("res.utils.gpu_utils.is_gpu_instance_type")
@patch("res.utils.gpu_utils.is_nvidia_gpu")
def test_is_amd_gpu_true(mock_nvidia, mock_gpu):
    mock_gpu.return_value = True
    mock_nvidia.return_value = False
    assert gpu_utils.is_amd_gpu("g4ad.xlarge") is True


@patch("res.utils.gpu_utils.is_gpu_instance_type")
@patch("res.utils.gpu_utils.is_nvidia_gpu")
def test_is_amd_gpu_false_not_gpu(mock_nvidia, mock_gpu):
    mock_gpu.return_value = False
    mock_nvidia.return_value = False
    assert gpu_utils.is_amd_gpu("t3.medium") is False
