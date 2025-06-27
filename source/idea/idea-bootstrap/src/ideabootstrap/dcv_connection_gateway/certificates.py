#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import grp
import os
import pwd
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import schedule
from OpenSSL import crypto
from res.resources import cluster_settings
from res.utils import logging_utils

DCV_CONNECTION_GATEWAY_CERT_DIR = "/etc/dcv-connection-gateway/certs/"

logger = logging_utils.get_logger("bootstrap")


def configure_certificates():
    logger.info("Configuring certificates...")

    timestamp = int(time.time())
    cert_content = cluster_settings.get_secret(
        "vdc.dcv_connection_gateway.certificate.certificate_secret_arn"
    )
    private_key_content = cluster_settings.get_secret(
        "vdc.dcv_connection_gateway.certificate.private_key_secret_arn"
    )

    cert_dir = Path(DCV_CONNECTION_GATEWAY_CERT_DIR)
    cert_dir.mkdir(parents=True, exist_ok=True)

    # Backup existing files if they exist
    cert_files = {
        "default_cert.pem": cert_dir / "default_cert.pem",
        "default_key_pkcs1.pem": cert_dir / "default_key_pkcs1.pem",
        "default_key_pkcs8.pem": cert_dir / "default_key_pkcs8.pem",
    }

    for file_name, file_path in cert_files.items():
        if file_path.exists():
            file_path.rename(f"{file_path}.{timestamp}")

    # Create new certificate files
    cert_path = cert_dir / "default_cert.pem"
    key_pkcs1_path = cert_dir / "default_key_pkcs1.pem"
    key_pkcs8_path = cert_dir / "default_key_pkcs8.pem"

    cert_path.write_text(cert_content)
    key_pkcs1_path.write_text(private_key_content)

    # Convert PKCS1 to PKCS8
    with open(key_pkcs1_path, "rb") as key_file:
        pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key_file.read())
        pkcs8_key = crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)

    with open(key_pkcs8_path, "wb") as f:
        f.write(pkcs8_key)

    # Set permissions
    for file_path in [cert_path, key_pkcs1_path, key_pkcs8_path]:
        os.chmod(file_path, 0o600)
        os.chown(
            file_path, pwd.getpwnam("dcvcgw").pw_uid, grp.getgrnam("dcvcgw").gr_gid
        )


def _refresh_certificates():
    try:
        cert_content = cluster_settings.get_secret(
            "vdc.dcv_connection_gateway.certificate.certificate_secret_arn"
        ).strip()
        private_key_content = cluster_settings.get_secret(
            "vdc.dcv_connection_gateway.certificate.private_key_secret_arn"
        ).strip()

        cert_dir = Path(DCV_CONNECTION_GATEWAY_CERT_DIR)
        cert_path = cert_dir / "default_cert.pem"
        key_path = cert_dir / "default_key_pkcs1.pem"

        # Check if current certificate and key contents match the new ones
        current_cert = cert_path.read_text().strip()
        current_key = key_path.read_text().strip()
        if current_cert == cert_content and current_key == private_key_content:
            logger.info(
                f"{datetime.now()}: Certificate and Private Key contents not changed. "
                "Skipping certificate reconfiguration and DCV Gateway restart."
            )
            return

        logger.info(
            f"{datetime.now()}: Certificate or Private Key contents or both have changed. "
            "Reconfiguring certificate and restarting DCV Gateway."
        )
        configure_certificates()

        # Restart DCV Gateway service
        subprocess.run(["systemctl", "restart", "dcv-connection-gateway"], check=True)
        logger.info("Refreshed certificate successfully.")
    except Exception as e:
        logger.error(f"Failed to refresh cert: {e}")


def _run_cert_refresh_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


def schedule_certificate_refresh():
    schedule.every().day.at("00:00").do(_refresh_certificates)

    # Create a separate thread for the scheduler
    scheduler_thread = threading.Thread(target=_run_cert_refresh_scheduler)
    scheduler_thread.daemon = True

    scheduler_thread.start()
