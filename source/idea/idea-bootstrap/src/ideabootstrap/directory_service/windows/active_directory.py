#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os
import subprocess
import winreg
from typing import Any, Dict

from res.resources import cluster_settings


def join_active_directory(auth_entry: Dict[str, Any], logger: logging.Logger) -> None:
    otp = auth_entry["otp"]
    ad_domain_name = cluster_settings.get_setting("directoryservice.name")

    logger.info(
        f"[Join AD] authorization successful. joining AD, Domain: {ad_domain_name}, OTP: {otp} ..."
    )

    # Add computer to domain
    ps_command = [
        "powershell.exe",
        "-Command",
        f"""
        $joinCred = New-Object pscredential -ArgumentList ([pscustomobject]@{{
            UserName = $null
            Password = (ConvertTo-SecureString -String {otp} -AsPlainText -Force)[0]
        }})
        Add-Computer -Domain {ad_domain_name} -Options UnsecuredJoin, PasswordPass -Credential $joinCred
        """,
    ]
    try:
        result = subprocess.run(ps_command, check=True, capture_output=True, text=True)
        logger.info(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to join AD: {e.stderr}")

    modify_logon_registry(logger)


def modify_logon_registry(logger: logging.Logger):
    key_path = r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
    domain_user_name = rf'{cluster_settings.get_setting("directoryservice.ad_short_name")}\{os.getenv("SESSION_OWNER")}'

    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "AutoAdminLogon", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "DefaultUserName", 0, winreg.REG_SZ, domain_user_name)
        winreg.CloseKey(key)

        logger.info("Logon registry set successfully")

    except WindowsError as e:
        logger.error(f"Error modifying logon registry: {e}")


def is_in_active_directory(logger: logging.Logger) -> bool:
    ps_command = [
        "powershell.exe",
        "-Command",
        "(Get-WmiObject -Class Win32_ComputerSystem).PartOfDomain",
    ]
    try:
        result = subprocess.run(ps_command, check=True, capture_output=True, text=True)
        return result.stdout.rstrip() == "True"
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to check whether the VDI has joined AD: {e.stderr}")
        return False

def connect_to_active_directory(_logger: logging.Logger):
    pass

def configure_sssd(_logger: logging.Logger):
    pass
