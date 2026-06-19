#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
from xml.sax.saxutils import escape as xml_escape

from res.app.middleware.form_to_json_xml_response_middleware import (
    FormToJsonXmlResponseMiddleware,
)
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient


def _xml_formatter(data: dict) -> str:
    result = data.get("result", "no")
    if result == "yes":
        return f'<auth result="yes"><username>{xml_escape(data.get("username", ""))}</username></auth>'
    return f'<auth result="no"><message>{xml_escape(data.get("message", "failed"))}</message></auth>'


_FIELD_MAPPING = {
    "sessionId": "session_id",
    "authenticationToken": "auth_token",
    "clientAddress": "client_address",
}

_ROUTE_CONFIG = ("POST", "/", _FIELD_MAPPING, _xml_formatter)


async def echo_handler(request: Request) -> JSONResponse:
    body = await request.json()
    return JSONResponse(body)


async def auth_handler(request: Request) -> JSONResponse:
    body = await request.json()
    return JSONResponse({"result": "yes", "username": body.get("session_id", "")})


async def error_handler(request: Request) -> JSONResponse:
    return JSONResponse({"message": "bad request"}, status_code=400)


async def health_handler(request: Request) -> JSONResponse:
    return JSONResponse({"status": "OK"})


def _create_app(routes_config=None, handlers=None):
    if handlers is None:
        handlers = [
            Route("/", echo_handler, methods=["POST"]),
            Route("/health", health_handler, methods=["GET"]),
        ]
    app = Starlette(routes=handlers)
    app.add_middleware(
        FormToJsonXmlResponseMiddleware,
        routes=routes_config or [_ROUTE_CONFIG],
    )
    return TestClient(app)


class TestFormToJsonXmlResponseMiddleware:

    def test_converts_form_urlencoded_to_json(self):
        client = _create_app()
        response = client.post(
            "/",
            data="sessionId=ses-123&authenticationToken=tok-456&clientAddress=10.0.0.1",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"
        assert "<auth" in response.text

    def test_field_mapping(self):
        client = _create_app()
        response = client.post(
            "/",
            data="sessionId=ses-123&authenticationToken=tok-456&clientAddress=10.0.0.1",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        # echo_handler returns the JSON body as-is, which gets formatted to XML
        # Since echo returns the mapped keys, result won't be "yes", so we get "no"
        assert 'result="no"' in response.text

    def test_successful_auth_response(self):
        client = _create_app(
            handlers=[
                Route("/", auth_handler, methods=["POST"]),
                Route("/health", health_handler, methods=["GET"]),
            ]
        )
        response = client.post(
            "/",
            data="sessionId=testuser&authenticationToken=tok&clientAddress=10.0.0.1",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert 'result="yes"' in response.text
        assert "<username>testuser</username>" in response.text

    def test_json_request_passes_through(self):
        client = _create_app()
        response = client.post(
            "/",
            json={
                "session_id": "ses-123",
                "auth_token": "tok",
                "client_address": "10.0.0.1",
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_non_matching_route_passes_through(self):
        client = _create_app()
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}
        assert "application/json" in response.headers["content-type"]

    def test_missing_form_fields_default_to_empty(self):
        client = _create_app()
        response = client.post(
            "/",
            data="sessionId=ses-123",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"

    def test_xml_escapes_special_characters(self):
        client = _create_app(
            handlers=[
                Route("/", auth_handler, methods=["POST"]),
                Route("/health", health_handler, methods=["GET"]),
            ]
        )
        response = client.post(
            "/",
            data="sessionId=<script>alert(1)</script>&authenticationToken=tok&clientAddress=10.0.0.1",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert "<script>" not in response.text
        assert "&lt;script&gt;" in response.text

    def test_error_status_code_passes_through_unchanged(self):
        client = _create_app(
            handlers=[
                Route("/", error_handler, methods=["POST"]),
                Route("/health", health_handler, methods=["GET"]),
            ]
        )
        response = client.post(
            "/",
            data="sessionId=ses-123&authenticationToken=tok&clientAddress=10.0.0.1",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 400
        assert "application/json" in response.headers["content-type"]

    def test_malformed_json_response_uses_empty_dict_fallback(self):
        async def bad_json_handler(request: Request):
            from starlette.responses import Response

            return Response(content="not-json", media_type="text/plain")

        client = _create_app(
            handlers=[
                Route("/", bad_json_handler, methods=["POST"]),
                Route("/health", health_handler, methods=["GET"]),
            ]
        )
        response = client.post(
            "/",
            data="sessionId=ses-123&authenticationToken=tok&clientAddress=10.0.0.1",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"
        # Fallback: xml_formatter({}) produces default "no" result
        assert 'result="no"' in response.text

    def test_parameterized_route_matches(self):
        route_config = (
            "POST",
            "/externalAuth/{resSessionId}",
            _FIELD_MAPPING,
            _xml_formatter,
        )
        client = _create_app(
            routes_config=[route_config],
            handlers=[
                Route("/externalAuth/{res_session_id}", auth_handler, methods=["POST"]),
                Route("/health", health_handler, methods=["GET"]),
            ],
        )
        response = client.post(
            "/externalAuth/ses-123",
            data="sessionId=console&authenticationToken=tok&clientAddress=10.0.0.1",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"
        assert 'result="yes"' in response.text

    def test_parameterized_route_does_not_match_other_paths(self):
        route_config = (
            "POST",
            "/externalAuth/{resSessionId}",
            _FIELD_MAPPING,
            _xml_formatter,
        )
        client = _create_app(
            routes_config=[route_config],
            handlers=[
                Route("/other-path", echo_handler, methods=["POST"]),
                Route("/health", health_handler, methods=["GET"]),
            ],
        )
        response = client.post(
            "/other-path",
            json={
                "session_id": "ses-123",
                "auth_token": "tok",
                "client_address": "10.0.0.1",
            },
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
