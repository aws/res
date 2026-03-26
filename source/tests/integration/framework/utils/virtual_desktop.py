import json
from typing import Any, Dict

from ideadatamodel import VirtualDesktopSoftwareStack  # type: ignore
from tests.integration.framework.utils.ec2_utils import get_latest_x86_amzn2023_ami_id


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
        "idea_session_created_on": "1735578106382",
        "actor_type": "USER",
        "permission_profile": {"profile_id": "test-profile-123"},
    }

    # Apply overrides
    if overrides:
        base_payload.update(overrides)

    return base_payload


def api_model_to_ideadatamodel(api_stack: Any) -> VirtualDesktopSoftwareStack:
    """Convert API model VirtualDesktopSoftwareStack to ideadatamodel VirtualDesktopSoftwareStack"""

    # Convert API model to dict, then to ideadatamodel
    if hasattr(api_stack, "to_dict"):
        stack_dict = api_stack.to_dict()
    else:
        # Fallback: convert to JSON and back to dict
        stack_dict = json.loads(json.dumps(api_stack, default=str))

    return VirtualDesktopSoftwareStack(**stack_dict)
