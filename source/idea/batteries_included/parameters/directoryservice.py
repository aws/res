#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Code changes made to this file must be replicated in 'source/idea/infrastructure/install/parameters/directoryservice' too

from dataclasses import dataclass
from typing import Any, Optional

from idea.infrastructure.install.constants import OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX
from idea.infrastructure.install.parameters.base import Attributes, Base, Key


class DirectoryServiceKey(Key):
    NAME = "ActiveDirectoryName"
    LDAP_BASE = "LDAPBase"
    AD_SHORT_NAME = "ADShortName"
    LDAP_CONNECTION_URI = "LDAPConnectionURI"
    USERS_OU = "UsersOU"
    GROUPS_OU = "GroupsOU"
    COMPUTERS_OU = "ComputersOU"
    SUDOERS_GROUP_NAME = "SudoersGroupName"
    SERVICE_ACCOUNT_PASSWORD = "ServiceAccountPassword"
    SERVICE_ACCOUNT_CREDENTIALS_SECRET_ARN = "ServiceAccountCredentialsSecretArn"
    DOMAIN_TLS_CERTIFICATE_SECRET_ARN = "DomainTLSCertificateSecretArn"
    ENABLE_LDAP_ID_MAPPING = "EnableLdapIDMapping"
    DISABLE_AD_JOIN = "DisableADJoin"
    ROOT_USER_DN = "ServiceAccountUserDN"


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
    sudoers_group_name: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.SUDOERS_GROUP_NAME,
            type="AWS::SSM::Parameter::Value<String>",
            description="Please provide parameter store path to contain group name of users who will be able to sudo in your active directory",
        )
    )
    service_account_password: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.SERVICE_ACCOUNT_PASSWORD,
            type="String",
            description="Please provide Directory Service Root (Service Account) password",
            no_echo=True,
        )
    )
    service_account_credentials_secret_arn: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.SERVICE_ACCOUNT_CREDENTIALS_SECRET_ARN,
            type="AWS::SSM::Parameter::Value<String>",
            description="Directory Service Account Credentials Secret ARN",
        )
    )
    domain_tls_certificate_secret_arn: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN,
            type="String",
            description="AD Domain TLS Certificate Secret ARN",
        )
    )
    enable_ldap_id_mapping: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.ENABLE_LDAP_ID_MAPPING,
            type="String",
            description="Set to False to use the uidNumbers and gidNumbers for users and group from the provided AD. Otherwise set to True.",
            allowed_values=["True", "False", ""],
        )
    )
    disable_ad_join: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.DISABLE_AD_JOIN,
            type="String",
            description="When set to True, prevents Linux and Windows hosts from automatically joining the Directory Domain. Windows instances require domain joining to launch successfully. If this setting is set to True, you must implement custom domain-join logic in your Windows instance launch scripts. Linux instances can launch with or without domain joining.",
            allowed_values=["True", "False", ""],
        )
    )
    root_user_dn: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.ROOT_USER_DN,
            type="AWS::SSM::Parameter::Value<String>",
            description="Provide the Distinguished name (DN) of the service account user in the Active Directory",
            no_echo=True,
        )
    )

    # These will be populated after the secrets are created from the above parameters
    root_user_dn_secret_arn: Optional[str] = None


class DirectoryServiceParameterGroups:
    parameter_group_for_directory_service: dict[str, Any] = {
        "Label": {
            "default": f"Active Directory details{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        "Parameters": [
            DirectoryServiceKey.NAME.value,
            DirectoryServiceKey.AD_SHORT_NAME.value,
            DirectoryServiceKey.LDAP_BASE.value,
            DirectoryServiceKey.LDAP_CONNECTION_URI.value,
            DirectoryServiceKey.SERVICE_ACCOUNT_PASSWORD.value,
            DirectoryServiceKey.SERVICE_ACCOUNT_CREDENTIALS_SECRET_ARN.value,
            DirectoryServiceKey.USERS_OU.value,
            DirectoryServiceKey.GROUPS_OU.value,
            DirectoryServiceKey.SUDOERS_GROUP_NAME.value,
            DirectoryServiceKey.COMPUTERS_OU.value,
            DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN.value,
            DirectoryServiceKey.ENABLE_LDAP_ID_MAPPING.value,
            DirectoryServiceKey.DISABLE_AD_JOIN.value,
            DirectoryServiceKey.ROOT_USER_DN.value,
        ],
    }


class DirectoryServiceParameterLabels:
    parameter_labels_for_directory_service: dict[str, Any] = {
        DirectoryServiceKey.NAME.value: {
            "default": f"{DirectoryServiceKey.NAME.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.AD_SHORT_NAME.value: {
            "default": f"{DirectoryServiceKey.AD_SHORT_NAME.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.LDAP_BASE.value: {
            "default": f"{DirectoryServiceKey.LDAP_BASE.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.LDAP_CONNECTION_URI.value: {
            "default": f"{DirectoryServiceKey.LDAP_CONNECTION_URI.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.SERVICE_ACCOUNT_PASSWORD.value: {
            "default": f"{DirectoryServiceKey.SERVICE_ACCOUNT_PASSWORD.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.SERVICE_ACCOUNT_CREDENTIALS_SECRET_ARN.value: {
            "default": f"{DirectoryServiceKey.SERVICE_ACCOUNT_CREDENTIALS_SECRET_ARN.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.USERS_OU.value: {
            "default": f"{DirectoryServiceKey.USERS_OU.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.GROUPS_OU.value: {
            "default": f"{DirectoryServiceKey.GROUPS_OU.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.SUDOERS_GROUP_NAME.value: {
            "default": f"{DirectoryServiceKey.SUDOERS_GROUP_NAME.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.COMPUTERS_OU.value: {
            "default": f"{DirectoryServiceKey.COMPUTERS_OU.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN.value: {
            "default": f"{DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.ENABLE_LDAP_ID_MAPPING.value: {
            "default": f"{DirectoryServiceKey.ENABLE_LDAP_ID_MAPPING.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.DISABLE_AD_JOIN.value: {
            "default": f"{DirectoryServiceKey.DISABLE_AD_JOIN.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
        DirectoryServiceKey.ROOT_USER_DN.value: {
            "default": f"{DirectoryServiceKey.ROOT_USER_DN.value}{OPTIONAL_INPUT_PARAMETER_LABEL_SUFFIX}"
        },
    }
