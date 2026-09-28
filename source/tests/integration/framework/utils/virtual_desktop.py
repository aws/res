from typing import Any, Dict, List, Optional

import pytest

from tests.integration.framework.utils.ec2_utils import get_latest_x86_amzn2023_ami_id


def parametrize_software_stacks(
    stacks: List[Any],
    xfail_os: Optional[Dict[str, str]] = None,
) -> List[Any]:
    """
    Build a pytest parametrize list from software stacks with optional xfail
    markers for known-broken OS/instance combinations.

    Args:
        stacks: List of VirtualDesktopSoftwareStack objects.
        xfail_os: Dict mapping base_os values to xfail reason strings.
            Stacks matching these OSes are wrapped with pytest.mark.xfail(strict=False).

    Returns:
        List suitable for @pytest.mark.parametrize("software_stack", ..., indirect=True).
    """
    xfail_os = xfail_os or {}
    params = []
    for stack in stacks:
        base_os = getattr(stack.base_os, "value", stack.base_os)
        param = (stack, "project", "admin")
        if base_os in xfail_os:
            params.append(
                pytest.param(
                    param,
                    marks=pytest.mark.xfail(reason=xfail_os[base_os], strict=False),
                )
            )
        else:
            params.append(pytest.param(param))
    return params


def get_software_stack_base_payload(region: str, **overrides: Any) -> Dict[str, Any]:
    """Create base payload with optional overrides"""
    ami_id = get_latest_x86_amzn2023_ami_id(region)

    base_payload = {
        "software_stack": {
            "name": "basic-software-stack",
            "description": "Basic project session",
            "ami_id": ami_id,
            "base_os": "amzn2023",
            "gpu": "NO_GPU",
            "min_storage": {"value": 100, "unit": "gb"},
            "min_ram": {"value": 22, "unit": "gb"},
            "placement": {"tenancy": "default"},
            "projects": [],
            "allowed_instance_types": [],
        }
    }

    # Apply overrides
    if overrides:
        base_payload["software_stack"].update(overrides)

    return base_payload


def get_permission_profile_base_payload(
    profile_id: str, **overrides: Any
) -> Dict[str, Any]:
    """Create base payload with optional overrides"""

    base_payload = {
        "profile": {
            "profile_id": profile_id,
            "title": "Test Permission Profile",
            "description": "Test permission profile for integration testing",
            "permissions": [{"key": "audio_in", "name": "Audio in", "enabled": True}],
        }
    }

    # Apply overrides
    if overrides:
        base_payload["profile"].update(overrides)

    return base_payload


def get_session_permission_base_payload(**overrides: Any) -> Dict[str, Any]:
    """Create base session permission payload with optional overrides"""
    base_payload = {
        "idea_session_id": "test-session-123",
        "idea_session_owner": "testuser",
        "idea_session_name": "test-session",
        "actor_name": "testactor",
        "idea_session_instance_type": "t3.medium",
        "idea_session_state": "READY",
        "idea_session_base_os": "amzn2023",
        "idea_session_hibernation_enabled": True,
        "idea_session_type": "VIRTUAL",
        "idea_session_created_on": "2024-12-30T18:21:46+00:00",
        "actor_type": "USER",
        "permission_profile": {"profile_id": "test-profile-123"},
    }

    # Apply overrides
    if overrides:
        base_payload.update(overrides)

    return base_payload
