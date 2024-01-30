#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass
from typing import Any

from idea.infrastructure.install.parameters import (
    common,
    customdomain,
    directoryservice,
    shared_storage,
)


@dataclass
class RESParameters(
    common.CommonParameters,
    customdomain.CustomDomainParameters,
    directoryservice.DirectoryServiceParameters,
    shared_storage.SharedStorageParameters,
):
    """
    This is where all the different categories of parameters are combined
    using inheritance.
    """

    pass


class AllRESParameterGroups(
    common.CommonParameterGroups,
    customdomain.CustomDomainParameterGroups,
    directoryservice.DirectoryServiceParameterGroups,
    shared_storage.SharedStorageParameterGroups,
):
    """
    All the parameter groups are collated here
    """

    @classmethod
    def template_metadata(cls) -> dict[str, Any]:
        return {
            "AWS::CloudFormation::Interface": {
                "ParameterGroups": [
                    common.CommonParameterGroups.parameter_group_for_environment_and_installer_details,
                    common.CommonParameterGroups.parameter_group_for_network_configuration,
                    directoryservice.DirectoryServiceParameterGroups.parameter_group_for_directory_service,
                    shared_storage.SharedStorageParameterGroups.parameter_group_for_shared_storage,
                    customdomain.CustomDomainParameterGroups.parameter_group_for_custom_domain,
                ]
            }
        }
