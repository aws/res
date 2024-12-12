#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
from dataclasses import dataclass
from typing import Any

from idea.batteries_included.parameters import (
    common,
    customdomain,
    directoryservice,
    internet_proxy,
    shared_storage,
)


@dataclass
class BIParameters(
    common.CommonParameters,
    customdomain.CustomDomainParameters,
    directoryservice.DirectoryServiceParameters,
    shared_storage.SharedStorageParameters,
    internet_proxy.InternetProxyParameters,
):
    """
    This is where all the different categories of parameters are combined
    using inheritance.
    """

    pass


class AllBIParameterGroups(
    common.CommonParameterGroups,
    customdomain.CustomDomainParameterGroups,
    directoryservice.DirectoryServiceParameterGroups,
    shared_storage.SharedStorageParameterGroups,
    internet_proxy.InternetProxyParameterGroups,
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
                    shared_storage.SharedStorageParameterGroups.parameter_group_for_shared_storage,
                    directoryservice.DirectoryServiceParameterGroups.parameter_group_for_directory_service,
                    customdomain.CustomDomainParameterGroups.parameter_group_for_custom_domain,
                ],
                "ParameterLabels": {
                    **common.CommonParameterLabels.parameter_labels_for_environment_and_installer_details,
                    **customdomain.CustomDomainParameterLabels.parameter_labels_for_custom_domain,
                    **directoryservice.DirectoryServiceParameterLabels.parameter_labels_for_directory_service,
                    **internet_proxy.InternetProxyParameterLabels.parameter_labels_for_internet_proxy,
                },
            },
        }
