#!/usr/bin/env python3
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
import os
import time
import json
import argparse
import subprocess
import requests
from datetime import datetime
from typing import Dict, Any
import psutil
import logging

from iam_auth import IAMAuth

IDLE_TICK_FILE = "C:\RES\.idle_tick" if os.name == "nt" else "/opt/res/.idle_tick"
IDLE_TIMEOUT_BUFFER = 20


def _get_uptime() -> float:
    """Returns the system uptime in seconds."""
    try:
        if os.name == "nt":  # Windows
            return (
                datetime.now() - datetime.fromtimestamp(psutil.boot_time())
            ).total_seconds()
        else:  # Linux
            with open("/proc/uptime", "r") as f:
                return float(f.readline().split()[0])
    except (ImportError, AttributeError, IOError, ValueError) as e:
        raise RuntimeError("Error getting uptime") from e


def _get_cpu_utilization() -> float:
    """Returns the current CPU utilization as a percentage."""
    params: Dict[str, Any] = {"interval": 1} if os.name == "nt" else {"percpu": False}
    return psutil.cpu_percent(**params)


def _get_dcv_latest_interaction_time() -> float:
    """Returns the last interaction time of the DCV session in epoch seconds."""
    dcv_program = "C:\\Program Files\\NICE\\DCV\\Server\\bin\\dcv.exe" if os.name == "nt" else "dcv"

    try:
        session_data = json.loads(
            subprocess.check_output([dcv_program, "list-sessions", "-j"], text=True)
        )
        session_connections = [
            json.loads(
                subprocess.check_output(
                    [dcv_program, "list-connections", session["id"], "-j"], text=True
                )
            )
            for session in session_data
        ]

        # Find the latest interaction time
        return max(
            (
                datetime.fromisoformat(
                    connection["last-interaction-time"].replace("Z", "+00:00")
                ).timestamp()
                for session in session_connections
                for connection in session
            ),
            default=0,
        )

    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        raise RuntimeError("Error checking DCV sessions") from e


def _is_idle(cpu_threshold: int) -> bool:
    if _get_cpu_utilization() > cpu_threshold:
        logging.info("CPU utilization is above threshold. System is not idle.")
        return False

    if _get_dcv_latest_interaction_time() + IDLE_TIMEOUT_BUFFER > time.time():
        logging.info("User activities detected. System is not idle.")
        return False

    logging.info("System is idle.")
    return True

def _clear_idle_tick() -> None:
    if os.path.exists(IDLE_TICK_FILE):
        os.remove(IDLE_TICK_FILE)
        logging.info("Idle tick file cleared")

def _manage_idle_tick(is_idle: bool) -> None:
    file_exists = os.path.exists(IDLE_TICK_FILE)
    if is_idle and not file_exists:
        open(IDLE_TICK_FILE, "w").close()
        logging.info("Idle tick file created")
    elif not is_idle and file_exists:
        _clear_idle_tick()


def _check_idle_timeout(idle_timeout: int) -> bool:
    if os.path.exists(IDLE_TICK_FILE):
        idle_time = time.time() - os.path.getmtime(IDLE_TICK_FILE)
        logging.info(f"Current idle time: {idle_time} seconds")
        return idle_time > idle_timeout
    return False


def _call_vdi_helper_api(
    api_url: str, aws_region: str, transition_state: str
) -> Dict[str, Any]:
    """Call VDI helper APIGateway to stop the instance."""
    session = requests.Session()
    session.auth = IAMAuth(region_name=aws_region)
    try:
        response = session.post(
            api_url,
            params={"action": "vdi_auto_stop", "transition_state": transition_state},
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError("Error calling VDI helper API") from e


def main() -> None:
    parser = argparse.ArgumentParser(description="VDI Idle Management")
    parser.add_argument("--aws-region", required=True, help="AWS region")
    parser.add_argument("--api-url", required=True, help="URL of the API endpoint")
    parser.add_argument("--log-file", required=True, help="Path to the log file")
    parser.add_argument(
        "--cpu-threshold", type=int, required=True, help="CPU threshold percentage"
    )
    parser.add_argument(
        "--idle-timeout", type=int, required=True, help="Idle timeout in minutes"
    )
    parser.add_argument(
        "--uptime-minimum", type=int, required=True, help="Minimum uptime in seconds"
    )
    parser.add_argument(
        "--transition-state",
        required=True,
        choices=["Terminate", "Stop"],
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    args = parser.parse_args()
    idle_timeout_seconds = args.idle_timeout * 60

    # Set up logging
    logging.basicConfig(
        filename=args.log_file,
        level=args.log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.info("Starting VDI Idle Management")

    uptime_minutes = _get_uptime()/60
    if uptime_minutes < args.uptime_minimum:
        _clear_idle_tick()
        logging.info("System uptime is less than the minimum. Skipping idle check.")
        return

    is_idle = _is_idle(args.cpu_threshold)
    _manage_idle_tick(is_idle)

    if _check_idle_timeout(idle_timeout_seconds):
        logging.info("Idle timeout reached. Calling VDI helper API.")
        response_json = _call_vdi_helper_api(
            args.api_url, args.aws_region, args.transition_state
        )
        logging.info(
            f"API Response: {json.dumps(response_json, indent=4)}"
            if response_json
            else "Failed to get response from VDI helper API"
        )
    else:
        logging.info("Idle timeout not reached")


if __name__ == "__main__":
    main()
