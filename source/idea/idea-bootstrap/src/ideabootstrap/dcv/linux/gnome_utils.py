#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import pwd
import subprocess

from res.utils import logging_utils

logger = logging_utils.get_logger("bootstrap")

_EXTENSION_UUID = "no-startup-anim@res"

_EXTENSION_JS = """\
import * as Layout from 'resource:///org/gnome/shell/ui/layout.js';
export default class {
    enable() {
        Layout.LayoutManager.prototype._startupAnimation = async function() { return; };
    }
    disable() {}
}
"""

_METADATA = {
    "uuid": _EXTENSION_UUID,
    "name": "No Startup Animation",
    "description": "Disables GNOME Shell startup animation to prevent DCV resize race condition",
    "shell-version": ["47"],
}


def configure() -> None:
    """
    Install a GNOME Shell extension that disables the startup animation.

    GNOME Shell 47's startup animation can hang indefinitely when DCV resizes
    the screen during the animation's ensureAllocation() call. This race
    condition is more likely when the user's home directory is on a network
    filesystem (e.g. EFS), as the added I/O latency widens the timing window.
    The extension patches _startupAnimation to return immediately, eliminating
    the race.

    Only applies to AL2023 which ships GNOME Shell 47.
    """
    base_os = os.environ.get("RES_BASE_OS")
    if base_os != "amzn2023":
        logger.info(f"OS is {base_os}, skipping GNOME Shell startup animation fix (AL2023 only)")
        return

    session_owner = os.environ.get("IDEA_SESSION_OWNER")
    if not session_owner:
        logger.warning("IDEA_SESSION_OWNER not set, skipping GNOME Shell startup animation fix")
        return

    try:
        pw = pwd.getpwnam(session_owner)
    except KeyError:
        logger.warning(f"User {session_owner} not found, skipping GNOME Shell startup animation fix")
        return

    ext_dir = os.path.join(pw.pw_dir, ".local", "share", "gnome-shell", "extensions", _EXTENSION_UUID)

    try:
        result = subprocess.run(
            ["gnome-shell", "--version"], capture_output=True, text=True,
        )
        if result.returncode == 0:
            # Output format: "GNOME Shell 47.3"
            version = result.stdout.strip().split()[-1]
            if not version.startswith("47"):
                logger.warning(
                    f"GNOME Shell version is {version}, extension targets 47. "
                    "The extension may not load correctly."
                )
        else:
            logger.warning("Could not determine GNOME Shell version")

        ext_js_path = os.path.join(ext_dir, "extension.js")
        metadata_path = os.path.join(ext_dir, "metadata.json")
        metadata_content = json.dumps(_METADATA)

        # Extension files are on shared EFS — skip if already up to date
        if os.path.isfile(ext_js_path) and os.path.isfile(metadata_path):
            with open(ext_js_path) as f:
                existing_js = f.read()
            with open(metadata_path) as f:
                existing_meta = f.read()
            if existing_js == _EXTENSION_JS and existing_meta == metadata_content:
                logger.info("GNOME Shell no-startup-anim extension already up to date, skipping")
                return

        os.makedirs(ext_dir, exist_ok=True)

        with open(os.path.join(ext_dir, "extension.js"), "w") as f:
            f.write(_EXTENSION_JS)
        with open(os.path.join(ext_dir, "metadata.json"), "w") as f:
            json.dump(_METADATA, f)

        os.chown(os.path.join(pw.pw_dir, ".local"), pw.pw_uid, pw.pw_gid)
        os.chown(os.path.join(pw.pw_dir, ".local", "share"), pw.pw_uid, pw.pw_gid)
        gnome_shell_dir = os.path.join(pw.pw_dir, ".local", "share", "gnome-shell")
        for dirpath, dirnames, filenames in os.walk(gnome_shell_dir):
            os.chown(dirpath, pw.pw_uid, pw.pw_gid)
            for filename in filenames:
                os.chown(os.path.join(dirpath, filename), pw.pw_uid, pw.pw_gid)

        # Enable the extension by appending to enabled-extensions in dconf.
        # Use dbus-run-session to provide a D-Bus session since bootstrap
        # runs outside of a graphical session.
        env = os.environ.copy()
        env["HOME"] = pw.pw_dir

        result = subprocess.run(
            ["sudo", "-u", session_owner, "dbus-run-session",
             "gsettings", "get", "org.gnome.shell", "enabled-extensions"],
            capture_output=True, text=True, env=env,
        )

        current = result.stdout.strip() if result.returncode == 0 else "@as []"
        if _EXTENSION_UUID not in current:
            if current in ("@as []", "[]"):
                new_value = f"['{_EXTENSION_UUID}']"
            else:
                new_value = current.rstrip("]") + f", '{_EXTENSION_UUID}']"

            subprocess.run(
                ["sudo", "-u", session_owner, "dbus-run-session",
                 "gsettings", "set", "org.gnome.shell", "enabled-extensions",
                 new_value],
                check=True, capture_output=True, text=True, env=env,
            )

        logger.info(f"Installed GNOME Shell no-startup-anim extension for {session_owner}")
    except Exception as e:
        logger.error(f"Failed to install GNOME Shell no-startup-anim extension: {e}")
