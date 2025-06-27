#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from res.utils import logging_utils
import os
from res.resources import cluster_settings
from typing import List, Tuple
from OpenSSL import crypto

logger = logging_utils.get_logger("bootstrap")

def get_cert_key_and_file() -> Tuple[str, str]:
    cluster_home_dir = cluster_settings.get_setting("cluster.home_dir")
    certs_dir = os.path.join(cluster_home_dir, "certs")

    cert_key = os.path.join(certs_dir, "idea.key")
    cert_file = os.path.join(certs_dir, "idea.crt")

    return cert_key, cert_file


def setup():
    hosted_zone = cluster_settings.get_setting("cluster.route53.private_hosted_zone_name") or ""
    logger.info(f"Trying to generate idea cert for hosted zone: {hosted_zone}")

    cert_key, cert_file = get_cert_key_and_file()
    certs_dir = os.path.dirname(cert_file)
    os.makedirs(certs_dir, exist_ok=True)

    logger.info(f"Creating key file in: {cert_key} and cert file in: {cert_file}")
    if not os.path.isfile(cert_key):
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 4096)

        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "California"
        cert.get_subject().L = "Sunnyvale"
        cert.get_subject().O = "Organization"
        cert.get_subject().CN = "corp.com"
        # cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10*365*24*60*60)  # 10 years validity
        cert.set_issuer(cert.get_subject())  # Self-signed
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')

        with open(cert_file, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

        with open(cert_key, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))


        logger.info(f"Generating idea cert files, file: {cert_file} and key: {cert_file} for hosted zone: {hosted_zone}")
    else:
        logger.info(f"Certs file already created: {cert_file}")

    os.chmod(certs_dir, 0o600)

