#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import tempfile

from ideabootstrap import bootstrap_common

def test_file_content_exists():
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        content = "first\n"
        assert not bootstrap_common.file_content_exists(content, temp_file.name)

        temp_file.write(content)
        temp_file.flush()
        assert bootstrap_common.file_content_exists(content, temp_file.name)


def test_append_to_file():
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        content = "first\n"
        temp_file.write(content)
        temp_file.flush()
        append_content = "second"
        bootstrap_common.append_to_file(append_content, temp_file.name)
        assert bootstrap_common.file_content_exists(append_content, temp_file.name)


def test_overwrite_file():
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        content = "first\n"
        temp_file.write(content)
        temp_file.flush()
        overwrite_content = "second"
        bootstrap_common.overwrite_file(overwrite_content, temp_file.name)
        assert bootstrap_common.file_content_exists(overwrite_content, temp_file.name)
        assert not bootstrap_common.file_content_exists(content, temp_file.name)

def test_set_reboot_required(monkeypatch):
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(bootstrap_common, "REBOOT_REQUIRED_FILE_PATH", temp_file_name)

        bootstrap_common.set_reboot_required("message")

        with open(temp_file_name, "r") as f:
            assert "message\n" in f.readlines()

def test_set_reboot_required(monkeypatch):
    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        temp_file_name = temp_file.name
        monkeypatch.setattr(bootstrap_common, "REBOOT_REQUIRED_FILE_PATH", temp_file_name)

        bootstrap_common.set_reboot_required("message")

        with open(temp_file_name, "r") as f:
            assert "message\n" in f.readlines()
