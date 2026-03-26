#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch, Mock
import pytest

# Import the actual serializer
from datamodel.serializers.virtual_desktop_software_stack_serializer import VirtualDesktopSoftwareStackSerializer


class TestVirtualDesktopSoftwareStackSerializer:
    """Test cases for VirtualDesktopSoftwareStackSerializer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = VirtualDesktopSoftwareStackSerializer()

    def test_customize_to_ddb_with_all_fields(self):
        """Test _customize_to_ddb converts all complex fields correctly."""
        input_data = {
            "stack_id": "stack-123",
            "name": "Test Stack",
            "base_os": "amazonlinux2",
            "projects": [
                {"project_id": "project1", "name": "Project 1"},
                {"project_id": "project2", "name": "Project 2"}
            ],
            "min_storage": {
                "value": 100,
                "unit": "GB"
            },
            "min_ram": {
                "value": 8,
                "unit": "GB"
            },
            "placement": {
                "host_id": "host-123",
                "host_resource_group_arn": "arn:aws:resource-groups:us-west-2:123456789:group/test-group",
                "tenancy": "dedicated",
                "affinity": "host"
            }
        }

        result = self.serializer._customize_to_ddb(input_data)

        # Check that projects are converted to list of project IDs
        assert result["projects"] == ["project1", "project2"]
        
        # Check min_storage is flattened
        assert result["min_storage_value"] == 100
        assert result["min_storage_unit"] == "GB"
        
        # Check min_ram is flattened
        assert result["min_ram_value"] == 8
        assert result["min_ram_unit"] == "GB"
        
        # Check placement is flattened
        assert result["host_id"] == "host-123"
        assert result["host_resource_group_arn"] == "arn:aws:resource-groups:us-west-2:123456789:group/test-group"
        assert result["tenancy"] == "dedicated"
        assert result["affinity"] == "host"
        
        # Check that original nested objects are removed
        assert "min_storage" not in result
        assert "min_ram" not in result
        assert "placement" not in result

    def test_customize_to_ddb_with_empty_projects(self):
        """Test _customize_to_ddb handles empty projects list."""
        input_data = {
            "stack_id": "stack-123",
            "projects": []
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["projects"] == []
        assert result["stack_id"] == "stack-123"

    def test_customize_to_ddb_with_none_projects(self):
        """Test _customize_to_ddb handles None projects."""
        input_data = {
            "stack_id": "stack-123",
            "projects": None
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["projects"] == []
        assert result["stack_id"] == "stack-123"

    def test_customize_to_ddb_with_empty_min_storage(self):
        """Test _customize_to_ddb handles empty min_storage."""
        input_data = {
            "stack_id": "stack-123",
            "min_storage": {}
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["min_storage_value"] is None
        assert result["min_storage_unit"] is None
        assert "min_storage" not in result

    def test_customize_to_ddb_with_none_min_storage(self):
        """Test _customize_to_ddb handles None min_storage."""
        input_data = {
            "stack_id": "stack-123",
            "min_storage": None
        }

        result = self.serializer._customize_to_ddb(input_data)

        assert result["min_storage_value"] is None
        assert result["min_storage_unit"] is None
        assert "min_storage" not in result

    def test_customize_to_ddb_with_default_tenancy(self):
        """Test _customize_to_ddb sets default tenancy when missing."""
        input_data = {
            "stack_id": "stack-123",
            "placement": {}  # Missing tenancy
        }

        result = self.serializer._customize_to_ddb(input_data)

        # Should use VirtualDesktopTenancy.DEFAULT.value
        assert result["tenancy"] is not None
        assert "placement" not in result

    def test_customize_from_ddb_with_all_fields(self):
        """Test _customize_from_ddb reconstructs complex objects correctly."""
        input_data = {
            "stack_id": "stack-123",
            "name": "Test Stack",
            "projects": [{"project_id": "project1"}, {"project_id": "project2"}],
            "min_ram_value": 8,
            "min_ram_unit": "GB",
            "min_storage_value": 100,
            "min_storage_unit": "GB",
            "host_id": "host-123",
            "host_resource_group_arn": "arn:aws:resource-groups:us-west-2:123456789:group/test-group",
            "tenancy": "dedicated",
            "affinity": "host"
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert len(result["projects"]) == 2
        for project in result["projects"]:
            assert "project_id" in project
            
        assert result["min_ram"] == {
            "value": 8,
            "unit": "GB"
        }
        
        assert result["min_storage"] == {
            "value": 100,
            "unit": "GB"
        }
        
        assert result["placement"] == {
            "host_id": "host-123",
            "host_resource_group_arn": "arn:aws:resource-groups:us-west-2:123456789:group/test-group",
            "tenancy": "dedicated",
            "affinity": "host"
        }

    def test_customize_from_ddb_with_empty_projects(self):
        """Test _customize_from_ddb handles empty projects list."""
        input_data = {
            "stack_id": "stack-123",
            "projects": []
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["projects"] == []

    def test_customize_from_ddb_with_none_projects(self):
        """Test _customize_from_ddb handles None projects."""
        input_data = {
            "stack_id": "stack-123",
            "projects": None
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["projects"] == None

    def test_customize_from_ddb_with_none_values(self):
        """Test _customize_from_ddb handles None values in storage/ram/placement."""
        input_data = {
            "stack_id": "stack-123",
            "min_ram_value": None,
            "min_ram_unit": None,
            "min_storage_value": None,
            "min_storage_unit": None,
            "host_id": None,
            "host_resource_group_arn": None,
            "tenancy": None,
            "affinity": None
        }

        result = self.serializer._customize_from_ddb(input_data)

        assert result["min_ram"] == {"value": None, "unit": None}
        assert result["min_storage"] == {"value": None, "unit": None}
        assert result["placement"] == {
            "host_id": None,
            "host_resource_group_arn": None,
            "tenancy": None,
            "affinity": None
        }

    def test_customize_to_ddb_projects_without_project_id(self):
        """Test _customize_to_ddb handles projects missing project_id gracefully."""
        input_data = {
            "stack_id": "stack-123",
            "projects": [
                {"name": "Project 1"},  # Missing project_id
                {"project_id": "project2", "name": "Project 2"}
            ]
        }

        result = self.serializer._customize_to_ddb(input_data)

        # Should handle missing project_id gracefully (gets None)
        assert result["projects"] == [None, "project2"]
