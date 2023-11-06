#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

# Sanic CORS Configuration
# Refer: https://sanic.dev/en/guide/how-to/cors.html#options.py

from ideasdk.server.cors import _add_cors_headers

from collections import defaultdict
from typing import Dict, FrozenSet, Optional

from sanic import Sanic, response
from sanic.router import Route
import ssl


# Only allow secure ciphers, notably leaving out AES-CBC mode
# OpenSSL chooses ECDSA or RSA depending on the cert in use
CIPHERS_TLS12 = [
    "ECDHE-ECDSA-CHACHA20-POLY1305",
    "ECDHE-ECDSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-RSA-CHACHA20-POLY1305",
    "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-RSA-AES128-GCM-SHA256",
]

def create_ssl_context(
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
    password: Optional[str] = None,
) -> ssl.SSLContext:
    """Create a context with secure crypto and HTTP/1.1 in protocols."""
    context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers(":".join(CIPHERS_TLS12))
    context.set_alpn_protocols(["http/1.1"])
    context.sni_callback = server_name_callback
    if certfile and keyfile:
        context.load_cert_chain(certfile, keyfile, password)
    return context


def server_name_callback(
    sslobj: ssl.SSLObject, server_name: str, ctx: ssl.SSLContext
) -> None:
    """Store the received SNI as sslobj.sanic_server_name."""
    sslobj.sanic_server_name = server_name  # type: ignore


def _compile_routes_needing_options(
    routes: Dict[str, Route]
) -> Dict[str, FrozenSet]:
    needs_options = defaultdict(list)
    # This is 21.3 and later. You will need to change this for older versions.
    for route in routes.values():
        if "OPTIONS" not in route.methods:
            needs_options[route.uri].extend(route.methods)
    return {
        uri: frozenset(methods) for uri, methods in dict(needs_options).items()
    }


def _options_wrapper(handler, methods):
    def wrapped_handler(request, *_, **__):
        nonlocal methods
        return handler(request, methods)

    return wrapped_handler


async def options_handler(_, methods) -> response.HTTPResponse:
    resp = response.empty()
    _add_cors_headers(resp, methods)
    return resp


def setup_options(app: Sanic, _):
    app.router.reset()
    needs_options = _compile_routes_needing_options(app.router.routes_all)
    for uri, methods in needs_options.items():
        app.add_route(
            _options_wrapper(options_handler, methods),
            uri,
            methods=["OPTIONS"]
        )
    app.router.finalize()
