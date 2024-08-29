#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Code changes made to this file must be replicated in 'source/idea/batteries_included/parameters' too

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
    ROOT_PASSWORD_SECRET_ARN = "ServiceAccountPasswordSecretArn"
    DOMAIN_TLS_CERTIFICATE_SECRET_ARN = "DomainTLSCertificateSecretArn"
    ENABLE_LDAP_ID_MAPPING = "EnableLdapIDMapping"
    DISABLE_AD_JOIN = "DisableADJoin"
    ROOT_USER_DN = "ServiceAccountUserDN"


@dataclass
class DirectoryServiceParameters(Base):
    name: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.NAME,
            description=(
                "Please provide the Fully Qualified Domain Name (FQDN) for your Active Directory. "
                "For example, developer.res.hpc.aws.dev"
            ),
            allowed_pattern=r"(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)",
        )
    )
    ldap_base: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.LDAP_BASE,
            description=(
                "Please provide the Active Directory base string Distinguished Name (DN) "
                "For example, dc=developer,dc=res,dc=hpc,dc=aws,dc=dev"
            ),
            allowed_pattern=".+",
        )
    )
    ad_short_name: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.AD_SHORT_NAME,
            description="Please provide the short name in Active directory",
            allowed_pattern=".+",
        )
    )
    ldap_connection_uri: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.LDAP_CONNECTION_URI,
            description="Please provide the active directory connection URI (e.g. ldap://www.example.com)",
            allowed_pattern=".+",
        )
    )
    users_ou: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.USERS_OU,
            description=(
                "Please provide Users Organization Unit in your active directory "
                "for example, OU=Users,DC=RES,DC=example,DC=internal"
            ),
            allowed_pattern=".+",
        )
    )
    groups_ou: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.GROUPS_OU,
            description="Please provide user groups Oganization Unit in your active directory",
            allowed_pattern=".+",
        )
    )
    computers_ou: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.COMPUTERS_OU,
            description="Please provide Organization Unit for compute and storage servers in your active directory",
            allowed_pattern=".+",
        )
    )
    sudoers_ou: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.SUDOERS_OU,
            description="Please provide Organizal Unit for users who will be able to sudo in your active directory",
            allowed_pattern=".+",
        )
    )
    sudoers_group_name: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.SUDOERS_GROUP_NAME,
            type="String",
            description="Please provide group name of users who will be able to sudo in your active directory",
            allowed_pattern=".+",
        )
    )
    root_username: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.ROOT_USERNAME,
            type="String",
            description="Directory Service Root (Service Account) username",
            no_echo=True,
            allowed_pattern=".+",
        )
    )
    root_password_secret_arn: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.ROOT_PASSWORD_SECRET_ARN,
            type="String",
            description="Directory Service Root (Service Account) Password Secret ARN",
            allowed_pattern="^(?:arn:(?:aws|aws-us-gov|aws-cn):secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:[A-Za-z0-9\-\_\+\=\/\.\@]{1,519})?$",
            # Secret name can be 512 characters long and may include letters, numbers, and the following characters: /_+=.@-.
            # Secrets Manager automatically adds a hyphen and six random characters after the secret name at the end of the ARN.
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_CreateSecret.html#SecretsManager-CreateSecret-request-Name
        )
    )
    domain_tls_certificate_secret_arn: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN,
            type="String",
            description="(Optional) AD Domain TLS Certificate Secret ARN",
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
    disable_ad_join: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.DISABLE_AD_JOIN,
            type="String",
            description="Set to True to prevent linux hosts from joining the Directory Domain. Otherwise set to False",
            allowed_values=["True", "False"],
        )
    )
    root_user_dn: str = Base.parameter(
        Attributes(
            id=DirectoryServiceKey.ROOT_USER_DN,
            type="String",
            description="Provide the Distinguished name (DN) of the service account user in the Active Directory",
            allowed_pattern=".+",
            no_echo=True,
        )
    )

    # These will be populated after the secrets are created from the above parameters
    root_username_secret_arn: Optional[str] = None
    root_user_dn_secret_arn: Optional[str] = None


class DirectoryServiceParameterGroups:
    parameter_group_for_directory_service: dict[str, Any] = {
        "Label": {"default": "Active Directory details"},
        "Parameters": [
            DirectoryServiceKey.NAME,
            DirectoryServiceKey.AD_SHORT_NAME,
            DirectoryServiceKey.LDAP_BASE,
            DirectoryServiceKey.LDAP_CONNECTION_URI,
            DirectoryServiceKey.ROOT_USERNAME,
            DirectoryServiceKey.ROOT_PASSWORD_SECRET_ARN,
            DirectoryServiceKey.USERS_OU,
            DirectoryServiceKey.GROUPS_OU,
            DirectoryServiceKey.SUDOERS_OU,
            DirectoryServiceKey.SUDOERS_GROUP_NAME,
            DirectoryServiceKey.COMPUTERS_OU,
            DirectoryServiceKey.DOMAIN_TLS_CERTIFICATE_SECRET_ARN,
            DirectoryServiceKey.ENABLE_LDAP_ID_MAPPING,
            DirectoryServiceKey.DISABLE_AD_JOIN,
            DirectoryServiceKey.ROOT_USER_DN,
        ],
    }
