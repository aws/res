#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import List, Optional

import requests


class _ListSessionsResponse:
    def __init__(self, listing, next_token=None):
        self.listing = listing
        self.next_token = next_token


class _BatchSessionResponse:
    def __init__(self, successful_list=None, unsuccessful_list=None):
        self.successful_list = successful_list or []
        self.unsuccessful_list = unsuccessful_list or []


class _ListSoftwareStacksResponse:
    def __init__(self, listing, next_token=None):
        self.listing = listing
        self.next_token = next_token


class _SoftwareStackEnvelopeResponse:
    """Envelope used by create / update / get software_stack responses."""

    def __init__(self, software_stack):
        self.software_stack = software_stack


class _DeleteSoftwareStackResponse:
    def __init__(self, success: bool = True):
        self.success = success


class _PermissionProfileEnvelopeResponse:
    """Envelope used by create / get permission_profile responses."""

    def __init__(self, profile):
        self.profile = profile


class _DeletePermissionProfileResponse:
    def __init__(self, success: bool = True):
        self.success = success


def _permission_profile_not_found(profile_id: str) -> requests.HTTPError:
    """Build the ``requests.HTTPError`` the real client raises on 404."""
    response = requests.Response()
    response.status_code = 404
    response.reason = "Not Found"
    response._content = (
        f'{{"message": "Permission profile {profile_id} not found"}}'.encode("utf-8")
    )
    return requests.HTTPError(f"404 Not Found: profile {profile_id}", response=response)


class MockResApiClient:

    def __init__(self) -> None:
        self.sessions: List = []
        self.last_batch_stop_request = None
        self.last_batch_delete_request = None
        # Software stack state — tests populate ``software_stacks`` (each entry
        # exposes ``stack_id``, ``base_os``, ``name``, ``projects`` at minimum).
        self.software_stacks: List = []
        self.last_create_software_stack_request = None
        self.last_update_software_stack_request = None
        self.last_delete_software_stack_request = None
        # Permission profile state. Tests populate ``permission_profiles`` with
        # objects exposing ``profile_id`` (backend or legacy datamodel works).
        self.permission_profiles: List = []
        self.last_create_permission_profile_request = None
        self.last_delete_permission_profile_id: Optional[str] = None

    def list_sessions(
        self,
        state: Optional[str] = None,
        base_os: Optional[str] = None,
        session_name: Optional[str] = None,
        stack_id: Optional[str] = None,
        owner: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> _ListSessionsResponse:
        return _ListSessionsResponse(listing=list(self.sessions), next_token=None)

    def list_all_sessions(self, **kwargs) -> List:
        return list(self.sessions)

    def batch_delete_session(self, request_content):
        self.last_batch_delete_request = request_content
        deleted_ids = [s.idea_session_id for s in request_content.sessions]
        self.sessions = [
            s for s in self.sessions if s.idea_session_id not in deleted_ids
        ]
        return _BatchSessionResponse()

    def batch_stop_session(self, request_content):
        self.last_batch_stop_request = request_content
        stop_ids = [s.idea_session_id for s in request_content.sessions]
        for session in self.sessions:
            if session.idea_session_id in stop_ids:
                session.state = "STOPPING"
        return _BatchSessionResponse()

    def list_software_stacks(
        self,
        project_id: Optional[str] = None,
        base_os: Optional[str] = None,
        software_stack_name: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> _ListSoftwareStacksResponse:
        """Filter the in-memory list by the same fields the real API supports."""
        listing = list(self.software_stacks)
        if software_stack_name:
            listing = [
                s for s in listing if getattr(s, "name", None) == software_stack_name
            ]
        if base_os:
            listing = [s for s in listing if getattr(s, "base_os", None) == base_os]
        if project_id:
            listing = [
                s
                for s in listing
                if any(
                    getattr(p, "project_id", None) == project_id
                    for p in (getattr(s, "projects", None) or [])
                )
            ]
        return _ListSoftwareStacksResponse(listing=listing, next_token=None)

    def get_software_stack(
        self, stack_id: str, base_os: str
    ) -> _SoftwareStackEnvelopeResponse:
        for stack in self.software_stacks:
            if (
                getattr(stack, "stack_id", None) == stack_id
                and getattr(stack, "base_os", None) == base_os
            ):
                return _SoftwareStackEnvelopeResponse(software_stack=stack)
        return _SoftwareStackEnvelopeResponse(software_stack=None)

    def create_software_stack(self, request_content) -> _SoftwareStackEnvelopeResponse:
        self.last_create_software_stack_request = request_content
        stack = request_content.software_stack
        self.software_stacks.append(stack)
        return _SoftwareStackEnvelopeResponse(software_stack=stack)

    def update_software_stack(
        self, stack_id: str, request_content
    ) -> _SoftwareStackEnvelopeResponse:
        self.last_update_software_stack_request = request_content
        new_stack = request_content.software_stack
        for i, existing in enumerate(self.software_stacks):
            if getattr(existing, "stack_id", None) == stack_id:
                self.software_stacks[i] = new_stack
                break
        return _SoftwareStackEnvelopeResponse(software_stack=new_stack)

    def delete_software_stack(
        self, stack_id: str, request_content
    ) -> _DeleteSoftwareStackResponse:
        self.last_delete_software_stack_request = request_content
        self.software_stacks = [
            s for s in self.software_stacks if getattr(s, "stack_id", None) != stack_id
        ]
        return _DeleteSoftwareStackResponse(success=True)

    def create_permission_profile(
        self, request_content
    ) -> _PermissionProfileEnvelopeResponse:
        self.last_create_permission_profile_request = request_content
        profile = request_content.profile
        self.permission_profiles.append(profile)
        return _PermissionProfileEnvelopeResponse(profile=profile)

    def get_permission_profile(
        self, profile_id: str
    ) -> _PermissionProfileEnvelopeResponse:
        for profile in self.permission_profiles:
            if getattr(profile, "profile_id", None) == profile_id:
                return _PermissionProfileEnvelopeResponse(profile=profile)
        raise _permission_profile_not_found(profile_id)

    def delete_permission_profile(
        self, profile_id: str
    ) -> _DeletePermissionProfileResponse:
        self.last_delete_permission_profile_id = profile_id
        self.permission_profiles = [
            p
            for p in self.permission_profiles
            if getattr(p, "profile_id", None) != profile_id
        ]
        return _DeletePermissionProfileResponse(success=True)
