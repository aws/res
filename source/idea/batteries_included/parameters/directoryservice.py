#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Code changes made to this file must be replicated in 'source/idea/infrastructure/install/parameters/directoryservice' too

from dataclasses import dataclass
from typing import Any, Optional

from idea.infrastructure.install.parameters.base import Attributes, Base, Key


class DirectoryServiceKey(Key):
    NAME = "ActiveDirectoryName"
    LDAP_BASE = "LDAPBase"
    AD_SHORT_NAME = "ADShortName"
    LDAP_CONNECTION_URI = "LDAPConnectionURI"
    USERS_OU = "UsersOU"
    GROUPS_OU = "GroupsOU"
    COMPUTERS_OU = "ComputersOU"
    SUDOERS_OU = "SudoersOU"
    SUDOERS_GROUP_NAME = "SudoersGroupName"
    ROOT_USERNAME = "ServiceAccountUsername"
    ROOT_PASSWORD = "ServiceAccountPassword"
    DOMAIN_TLS_CERTIFICATE_SECRET_ARN = "DomainTLSCertificateSecretArn"
    ENABLE_LDAP_ID_MAPPING = "EnableLdapIDMapping"


@dataclass
class DirectoryServiceParameters(Base):
    name: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.NAME,
            type="AWS::SSM::Parameter::Value<String>",
            description=(
                "Please provide parameter store path to contain the Fully Qualified Domain Name (FQDN) for your Active Directory. "
            ),
        )
    )
    ldap_base: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.LDAP_BASE,
            type="AWS::SSM::Parameter::Value<String>",
            description=(
                "Please provide parameter store path to contain the Active Directory base string Distinguished Name (DN). "
            ),
        )
    )
    ad_short_name: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.AD_SHORT_NAME,
            type="AWS::SSM::Parameter::Value<String>",
            description="Please provide parameter store path to contain the short name in Active directory",
        )
    )
    ldap_connection_uri: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.LDAP_CONNECTION_URI,
            type="AWS::SSM::Parameter::Value<String>",
            description="Please provide parameter store path to contain the active directory connection URI (e.g. ldap://www.example.com)",
        )
    )
    users_ou: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.USERS_OU,
            type="AWS::SSM::Parameter::Value<String>",
            description=(
                "Please provide parameter store path to contain Users Organization Unit in your active directory "
            ),
        )
    )
    groups_ou: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.GROUPS_OU,
            type="AWS::SSM::Parameter::Value<String>",
            description="Please provide parameter store path to contain user groups Oganization Unit in your active directory",
        )
    )
    computers_ou: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.COMPUTERS_OU,
            type="AWS::SSM::Parameter::Value<String>",
            description="Please provide parameter store path to contain Organization Unit for compute and storage servers in your active directory",
        )
    )
    sudoers_ou: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.SUDOERS_OU,
            type="AWS::SSM::Parameter::Value<String>",
            description="Please provide parameter store path to contain Organization Unit for users who will be able to sudo in your active directory",
        )
    )
    sudoers_group_name: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.SUDOERS_GROUP_NAME,
            type="AWS::SSM::Parameter::Value<String>",
            description="Please provide parameter store path to contain group name of users who will be able to sudo in your active directory",
        )
    )
    root_username: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.ROOT_USERNAME,
            type="AWS::SSM::Parameter::Value<String>",
            description="Please provide parameter store path to contain Directory Service Root (Service Account) username",
            no_echo=True,
        )
    )
    root_password: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.ROOT_PASSWORD,
            type="String",
            description="Please provide Directory Service Root (Service Account) password",
            no_echo=True,
        )
    )
    domain_tls_certificate_secret_arn: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN,
            type="String",
            description="(Optional) Domain TLS Certificate Secret ARN",
        )
    )
    enable_ldap_id_mapping: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.ENABLE_LDAP_ID_MAPPING,
            type="String",
            description="Set to False to use the uidNumbers and gidNumbers for users and group from the provided AD. Otherwise set to True.",
            allowed_values=["True", "False"],
        )
    )

    # These will be populated after the secrets are created from the above parameters
    root_username_secret_arn: Optional[str] = None
    root_password_secret_arn: Optional[str] = None


class DirectoryServiceParameterGroups:
    parameter_group_for_directory_service: dict[str, Any] = {
        "Label": {"default": "Active Directory details"},
        "Parameters": [
            DirectoryServiceKey.NAME,
            DirectoryServiceKey.AD_SHORT_NAME,
            DirectoryServiceKey.LDAP_BASE,
            DirectoryServiceKey.LDAP_CONNECTION_URI,
            DirectoryServiceKey.ROOT_USERNAME,
            DirectoryServiceKey.ROOT_PASSWORD,
            DirectoryServiceKey.USERS_OU,
            DirectoryServiceKey.GROUPS_OU,
            DirectoryServiceKey.SUDOERS_OU,
            DirectoryServiceKey.SUDOERS_GROUP_NAME,
            DirectoryServiceKey.COMPUTERS_OU,
            DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN,
            DirectoryServiceKey.ENABLE_LDAP_ID_MAPPING,
        ],
    }
