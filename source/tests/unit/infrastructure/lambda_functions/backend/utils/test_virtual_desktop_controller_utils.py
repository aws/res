#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
import sys
import pytest

# Add the backend directory to Python path to match utils import context
backend_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../../../../idea/backend",
    )
)
sys.path.insert(0, backend_path)

from api.utils import virtual_desktop_controller_utils
from api.exceptions import BadRequestException


class TestVirtualDesktopControllerUtils:
    """Test class for virtual_desktop_controller_utils module - API validation functions only."""

    def test_validate_date_range_filter_valid_with_both_after_and_before(self):
        """Test validate_date_range_filter succeeds with valid after and before."""
        virtual_desktop_controller_utils.validate_date_range_filter(
            date_range_key="created_on", after="1000", before="2000"
        )

    def test_validate_date_range_filter_valid_with_only_after(self):
        """Test validate_date_range_filter succeeds with only after."""
        virtual_desktop_controller_utils.validate_date_range_filter(
            date_range_key="created_on", after="1000"
        )

    def test_validate_date_range_filter_valid_with_only_before(self):
        """Test validate_date_range_filter succeeds with only before."""
        virtual_desktop_controller_utils.validate_date_range_filter(
            date_range_key="created_on", before="2000"
        )

    def test_validate_date_range_filter_no_params(self):
        """Test validate_date_range_filter succeeds with no parameters."""
        virtual_desktop_controller_utils.validate_date_range_filter()

    def test_validate_date_range_filter_missing_date_range_key(self):
        """Test validate_date_range_filter raises exception when date_range_key is missing."""
        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller_utils.validate_date_range_filter(
                after="1000", before="2000"
            )
        
        assert "date_range_key is required when specifying after or before" in str(exc_info.value)

    def test_validate_date_range_filter_missing_after_and_before(self):
        """Test validate_date_range_filter raises exception when after and before are missing."""
        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller_utils.validate_date_range_filter(
                date_range_key="created_on"
            )
        
        assert "after and/or before is required when specifying date_range_key" in str(exc_info.value)

    def test_validate_date_range_filter_invalid_after_format(self):
        """Test validate_date_range_filter raises exception for invalid after format."""
        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller_utils.validate_date_range_filter(
                date_range_key="created_on", after="invalid", before="2000"
            )
        
        assert "after and before must be valid integer timestamps" in str(exc_info.value)

    def test_validate_date_range_filter_invalid_before_format(self):
        """Test validate_date_range_filter raises exception for invalid before format."""
        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller_utils.validate_date_range_filter(
                date_range_key="created_on", after="1000", before="invalid"
            )
        
        assert "after and before must be valid integer timestamps" in str(exc_info.value)

    def test_validate_date_range_filter_after_greater_than_before(self):
        """Test validate_date_range_filter raises exception when after > before."""
        with pytest.raises(BadRequestException) as exc_info:
            virtual_desktop_controller_utils.validate_date_range_filter(
                date_range_key="created_on", after="2000", before="1000"
            )
        
        assert "after must be less than or equal to before" in str(exc_info.value)
