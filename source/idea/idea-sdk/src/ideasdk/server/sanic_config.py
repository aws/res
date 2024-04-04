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

import sanic.config
import sys

SANIC_LOGGING_CONFIG = dict(
    version=1,
    disable_existing_loggers=False,
    loggers={
        "sanic.root": {"level": "ERROR", "handlers": ["sanic_console"]},
        "sanic.error": {
            "level": "ERROR",
            "handlers": ["sanic_error_console"],
            "propagate": True,
            "qualname": "sanic.error",
        },
        "sanic.access": {
            "level": "ERROR",
            "handlers": ["sanic_access_console"],
            "propagate": True,
            "qualname": "sanic.access",
        },
    },
    handlers={
        "sanic_console": {
            "class": "logging.StreamHandler",
            "formatter": "sanic_generic",
            "stream": sys.stdout,
        },
        "sanic_error_console": {
            "class": "logging.StreamHandler",
            "formatter": "sanic_generic",
            "stream": sys.stderr,
        },
        "sanic_access_console": {
            "class": "logging.StreamHandler",
            "formatter": "sanic_access",
            "stream": sys.stdout,
        },
    },
    formatters={
        "sanic_generic": {
            "format": "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
        "sanic_access": {
            "format": "%(asctime)s - (%(name)s)[%(levelname)s][%(host)s]: "
                      + "%(request)s %(message)s %(status)d %(byte)d",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        }
    }
)

SANIC_APP_CONFIG = sanic.config.Config({
    "ACCESS_LOG": False,
    "AUTO_EXTEND": True,
    "AUTO_RELOAD": False,
    "EVENT_AUTOREGISTER": True,
    "FORWARDED_FOR_HEADER": "X-Forwarded-For",
    "FORWARDED_SECRET": None,
    "GRACEFUL_SHUTDOWN_TIMEOUT": 15.0,  # 15 sec - not used, and is handled by SocaServer
    "KEEP_ALIVE_TIMEOUT": 15,  # 15 seconds - give time for follow-up requests
    "KEEP_ALIVE": True,
    "MOTD": True,
    "MOTD_DISPLAY": {},
    "NOISY_EXCEPTIONS": False,
    "PROXIES_COUNT": None,
    "REAL_IP_HEADER": None,
    "REGISTER": True,
    "REQUEST_BUFFER_SIZE": 65536,  # 64 KiB
    "REQUEST_MAX_HEADER_SIZE": 8192,  # 8 KiB, but cannot exceed 16384
    "REQUEST_ID_HEADER": "X-Request-ID",
    "REQUEST_MAX_SIZE": 10_000_000_000,  # 10 Gigabytes
    "REQUEST_TIMEOUT": 600,  # 10-min - large uploads over slow connections
    "RESPONSE_TIMEOUT": 600,  # 10-min - large uploads over slow connections
    "USE_UVLOOP": True,
    "WEBSOCKET_MAX_SIZE": 2 ** 20,  # 1 megabyte
    "WEBSOCKET_PING_INTERVAL": 20,
    "WEBSOCKET_PING_TIMEOUT": 20,
    "TOUCHUP": False,  # Allow starting multiple apps
})
