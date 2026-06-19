#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

"""
Serializers package for API <-> DDB conversions.

This package contains serializer classes for each Smithy model, providing
hooks for custom transformation logic between API data models and DynamoDB
dictionary formats.

Usage:
    from datamodel.serializers import permission_profile_serializer

    # Convert API model to DDB format
    ddb_data = permission_profile_serializer.to_ddb_dict(api_model)

    # Convert DDB record back to API format
    api_data = permission_profile_serializer.from_ddb_dict(ddb_record)
    api_model = PermissionProfile.from_dict(api_data)
"""

from datamodel.serializers.base_serializer import BaseSerializer, SerializerUtils

# Auto-generated imports
from .list_value_serializer import listvalue_serializer
from .permission_profile_serializer import permissionprofile_serializer
from .virtual_desktop_server_serializer import virtualdesktopserver_serializer
from .res_filter_serializer import resfilter_serializer
from .virtual_desktop_session_permission_serializer import virtualdesktopsessionpermission_serializer
from .virtual_desktop_schedule_serializer import virtualdesktopschedule_serializer
from .virtual_desktop_permission_serializer import virtualdesktoppermission_serializer
from .virtual_desktop_week_schedule_serializer import virtualdesktopweekschedule_serializer
from .virtual_desktop_software_stack_serializer import virtualdesktopsoftwarestack_serializer
from .res_filter_value_string_or_list_serializer import resfiltervaluestringorlist_serializer
from .virtual_desktop_permission_profile_serializer import virtualdesktoppermissionprofile_serializer
from .virtual_desktop_placement_serializer import virtualdesktopplacement_serializer
from .res_paginator_serializer import respaginator_serializer
from .res_date_range_serializer import resdaterange_serializer
from .res_memory_serializer import resmemory_serializer
from .string_value_serializer import stringvalue_serializer
from .virtual_desktop_session_serializer import virtualdesktopsession_serializer
from .project_serializer import project_serializer
from .res_sort_by_serializer import ressortby_serializer

__all__ = ['BaseSerializer', 'SerializerUtils', 'listvalue_serializer', 'permissionprofile_serializer', 'virtualdesktopserver_serializer', 'resfilter_serializer', 'virtualdesktopsessionpermission_serializer', 'virtualdesktopschedule_serializer', 'virtualdesktoppermission_serializer', 'virtualdesktopweekschedule_serializer', 'virtualdesktopsoftwarestack_serializer', 'resfiltervaluestringorlist_serializer', 'virtualdesktoppermissionprofile_serializer', 'virtualdesktopplacement_serializer', 'respaginator_serializer', 'resdaterange_serializer', 'resmemory_serializer', 'stringvalue_serializer', 'virtualdesktopsession_serializer', 'project_serializer', 'ressortby_serializer']
