#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from typing import Any

from idea.infrastructure.install.parameters.base import Attributes, Base, Key


class CustomDomainKey(Key):
    CUSTOM_DOMAIN_NAME_FOR_WEB_APP = "CustomDomainNameforWebApp"
    CUSTOM_DOMAIN_NAME_FOR_VDI = "CustomDomainNameforVDI"
    ACM_CERTIFICATE_ARN_FOR_WEB_APP = "ACMCertificateARNforWebApp"
    CERTIFICATE_SECRET_ARN_FOR_VDI = "CertificateSecretARNforVDI"
    PRIVATE_KEY_SECRET_ARN_FOR_VDI = "PrivateKeySecretARNforVDI"


@dataclass
class CustomDomainParameters(Base):
    custom_domain_name_for_web_ui: str = Base.parameter(
        Attributes(
            id=CustomDomainKey.CUSTOM_DOMAIN_NAME_FOR_WEB_APP,
            type="String",
            description=(
                "You may provide a custom domain name for web user interface, instead of default under amazonaws.com."
            ),
        )
    )

    custom_domain_name_for_vdi: str = Base.parameter(
        Attributes(
            id=CustomDomainKey.CUSTOM_DOMAIN_NAME_FOR_VDI,
            type="String",
            description=(
                "You may provide a custom domain name for VDI, instead of default under amazonaws.com."
            ),
        )
    )

    acm_certificate_arn_for_web_ui: str = Base.parameter(
        Attributes(
            id=CustomDomainKey.ACM_CERTIFICATE_ARN_FOR_WEB_APP,
            type="String",
            description=(
                (
                    "If you have provided a custom domain name for Web UI above then "
                    "please provide the Amazon Resource Name (ARN) for the "
                    "corresponding certificate stored in Amazon Certificate Manager (ACM)."
                )
            ),
        )
    )

    certificate_secret_arn_for_vdi_domain_name: str = Base.parameter(
        Attributes(
            id=CustomDomainKey.CERTIFICATE_SECRET_ARN_FOR_VDI,
            type="String",
            description=(
                (
                    "If you have provided a custom domain name for VDI above then "
                    "please provide the Amazon Resource Name (ARN) for the "
                    "certificate secret stored in AWS Secret Manager (ASM)."
                )
            ),
        )
    )

    private_key_secret_arn_for_vdi_domain_name: str = Base.parameter(
        Attributes(
            id=CustomDomainKey.PRIVATE_KEY_SECRET_ARN_FOR_VDI,
            type="String",
            description=(
                (
                    "If you have provided custom domain name for VDI above then "
                    "please provide Amazon Resource Name (ARN) for the "
                    "private key of the certificate stored in AWS Secret Manager (ASM)."
                )
            ),
        )
    )


class CustomDomainParameterGroups:
    parameter_group_for_custom_domain: dict[str, Any] = {
        "Label": {
            "default": "Custom domain details, only needed if you would like to use a custom domain"
        },
        "Parameters": [
            CustomDomainKey.CUSTOM_DOMAIN_NAME_FOR_WEB_APP,
            CustomDomainKey.CUSTOM_DOMAIN_NAME_FOR_VDI,
            CustomDomainKey.ACM_CERTIFICATE_ARN_FOR_WEB_APP,
            CustomDomainKey.CERTIFICATE_SECRET_ARN_FOR_VDI,
            CustomDomainKey.PRIVATE_KEY_SECRET_ARN_FOR_VDI,
        ],
    }
