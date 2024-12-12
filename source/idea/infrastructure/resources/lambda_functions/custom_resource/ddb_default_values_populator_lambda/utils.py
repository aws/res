#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, Dict

import yaml
from res.constants import ENVIRONMENT_NAME_KEY  # type: ignore

from .constants import REGIONAL_AMI_CONFIG, REGIONAL_TIMEZONE_CONFIG


def get_parameters_for_templates() -> Dict[str, Any]:
    input_parameters = get_input_parameters_from_environment()
    # These parameters are required for all template generation based on the current config files
    _add_hardcoded_parameters(input_parameters)
    _add_enabled_modules(input_parameters)
    _update_network_string_to_list(input_parameters)
    _update_subnets(input_parameters)
    _add_supported_os(input_parameters)
    _add_timezone(input_parameters)
    _add_instance_ami(input_parameters)
    _add_directory_service_params(input_parameters)
    _update_custom_certificates(input_parameters)
    return input_parameters


def _get_base_os() -> str:
    return "amazonlinux2"


def _add_instance_ami(input_parameters: Dict[str, Any]) -> None:
    if not input_parameters["instance_ami"]:
        region = input_parameters["aws_region"]
        with open(REGIONAL_AMI_CONFIG, "r") as f:
            regions_config = yaml.safe_load(f.read())
        ami_config = regions_config[region]
        if ami_config is None:
            raise Exception(f"Region: {region} not found in region_ami_config.yml")
        base_os = _get_base_os()
        ami_id = ami_config.get(base_os)
        if not ami_id:
            raise Exception(
                f"instance_ami not found for base_os: {base_os}, region: {region}"
            )
        input_parameters["instance_ami"] = ami_id


def _add_timezone(input_parameters: Dict[str, Any]) -> None:
    region = input_parameters["aws_region"]
    with open(REGIONAL_TIMEZONE_CONFIG, "r") as f:
        region_timezone_config = yaml.safe_load(f.read())
    region_timezone_id = region_timezone_config.get(region, "America/Los_Angeles")
    input_parameters["cluster_timezone"] = region_timezone_id


def _update_network_string_to_list(input_parameters: Dict[str, Any]) -> None:
    input_parameters["prefix_list"] = (
        [] if not input_parameters["prefix_list"] else [input_parameters["prefix_list"]]
    )
    input_parameters["client_ip"] = (
        [] if not input_parameters["client_ip"] else [input_parameters["client_ip"]]
    )


def _update_custom_certificates(input_parameters: Dict[str, Any]) -> None:
    if not input_parameters.get("webapp_custom_dns_name"):
        return
    certs_settings = [
        "webapp_custom_dns_name",
        "certificate_secret_arn",
        "acm_certificate_arn",
        "vdi_custom_dns_name",
        "private_key_secret_arn",
    ]
    all_present = True
    for setting in certs_settings:
        if not input_parameters.get(setting):
            all_present = False
    if all_present:
        input_parameters["alb_custom_certificate_provided"] = True
        input_parameters["alb_custom_certificate_acm_certificate_arn"] = (
            input_parameters["acm_certificate_arn"]
        )
        input_parameters["alb_custom_dns_name"] = input_parameters[
            "webapp_custom_dns_name"
        ]
        input_parameters["dcv_connection_gateway_custom_certificate_provided"] = True
        input_parameters["dcv_connection_gateway_custom_dns_hostname"] = (
            input_parameters["vdi_custom_dns_name"]
        )
        input_parameters[
            "dcv_connection_gateway_custom_certificate_certificate_secret_arn"
        ] = input_parameters["certificate_secret_arn"]
        input_parameters[
            "dcv_connection_gateway_custom_certificate_private_key_secret_arn"
        ] = input_parameters["private_key_secret_arn"]


def _add_directory_service_params(input_parameters: Dict[str, Any]) -> None:
    input_parameters["service_account_credentials_provided"] = (
        True if input_parameters["service_account_credentials_secret_arn"] else False
    )
    input_parameters["directory_service_service_account_credentials_secret_arn"] = (
        input_parameters["service_account_credentials_secret_arn"]
    )


def _update_subnets(input_parameters: Dict[str, Any]) -> None:
    load_balancer_subnet_ids = input_parameters["load_balancer_subnet_ids"].split(",")
    infrastructure_host_subnet_ids = input_parameters[
        "infrastructure_host_subnet_ids"
    ].split(",")
    vdi_subnet_ids = input_parameters["vdi_subnet_ids"].split(",")
    if not load_balancer_subnet_ids or not infrastructure_host_subnet_ids:
        raise Exception("Subnet IDs are required")
    if input_parameters["alb_public"] == "true":
        input_parameters["private_subnet_ids"] = infrastructure_host_subnet_ids
        input_parameters["public_subnet_ids"] = load_balancer_subnet_ids
        input_parameters["alb_public"] = True
    else:
        input_parameters["alb_public"] = False
        input_parameters["private_subnet_ids"] = list(
            set([*load_balancer_subnet_ids, *infrastructure_host_subnet_ids])
        )
        input_parameters["public_subnet_ids"] = ""
    input_parameters["load_balancer_subnet_ids"] = load_balancer_subnet_ids
    input_parameters["infrastructure_host_subnet_ids"] = infrastructure_host_subnet_ids
    input_parameters["vdi_subnet_ids"] = vdi_subnet_ids
    input_parameters["dcv_session_private_subnet_ids"] = vdi_subnet_ids


def _add_hardcoded_parameters(input_parameters: Dict[str, Any]) -> None:
    input_parameters["base_os"] = _get_base_os()
    input_parameters["volume_size"] = "200"
    input_parameters["instance_type"] = "m5.large"
    input_parameters["cluster_name"] = input_parameters[ENVIRONMENT_NAME_KEY]
    input_parameters["administrator_username"] = "clusteradmin"
    input_parameters["cluster_locale"] = "en_US"
    input_parameters["internal_mount_dir"] = "/internal"
    input_parameters["use_existing_vpc"] = True
    input_parameters["use_vpc_endpoints"] = True
    input_parameters["enable_aws_backup"] = False
    input_parameters["directory_service_provider"] = "activedirectory"
    input_parameters["identity_provider"] = "cognito-idp"
    input_parameters["storage_home_provider"] = "efs"
    input_parameters["use_existing_home_fs"] = True
    input_parameters["storage_internal_provider"] = "efs"
    input_parameters["home_mount_dir"] = "/home"
    input_parameters["dcv_session_quic_support"] = False
    input_parameters["kms_key_type"] = "aws-managed"
    input_parameters["metrics_provider"] = "cloudwatch"
    input_parameters["use_existing_directory_service"] = False
    input_parameters["use_existing_internal_fs"] = False


def _add_enabled_modules(input_parameters: Dict[str, Any]) -> None:
    enabled_modules = ["virtual-desktop-controller"]
    if input_parameters["alb_public"] == "true":
        enabled_modules.append("bastion-host")
    input_parameters["enabled_modules"] = enabled_modules


def _add_supported_os(input_parameters: Dict[str, Any]) -> None:
    input_parameters["supported_base_os"] = [
        "amazonlinux2",
        "rhel8",
        "rhel9",
        "ubuntu2204",
        "windows",
    ]


def get_input_parameters_from_environment() -> Dict[str, Any]:
    input_parameters = {
        # Essential environment variables
        "aws_partition": os.environ.get("aws_partition"),
        "aws_region": os.environ.get("aws_region"),
        "aws_account_id": os.environ.get("aws_account_id"),
        "aws_dns_suffix": os.environ.get("aws_dns_suffix"),
        ###### Stack Input parameters ######
        # Environment and installer details
        ENVIRONMENT_NAME_KEY: os.environ.get(ENVIRONMENT_NAME_KEY),
        "administrator_email": os.environ.get("administrator_email"),
        "instance_ami": os.environ.get("instance_ami"),
        "ssh_key_pair_name": os.environ.get("ssh_key_pair_name"),
        "client_ip": os.environ.get("client_ip"),
        "prefix_list": os.environ.get("prefix_list"),
        "permission_boundary_arn": os.environ.get("permission_boundary_arn"),
        # Network configuration for the RES environment
        "vpc_id": os.environ.get("vpc_id"),
        "alb_public": os.environ.get("alb_public"),
        "load_balancer_subnet_ids": os.environ.get("load_balancer_subnet_ids"),
        "infrastructure_host_subnet_ids": os.environ.get(
            "infrastructure_host_subnet_ids"
        ),
        "vdi_subnet_ids": os.environ.get("vdi_subnet_ids"),
        # Active Directory details
        "ad_name": os.environ.get("ad_name"),
        "ad_short_name": os.environ.get("ad_short_name"),
        "ldap_base": os.environ.get("ldap_base"),
        "ldap_connection_uri": os.environ.get("ldap_connection_uri"),
        "service_account_credentials_secret_arn": os.environ.get(
            "service_account_credentials_secret_arn"
        ),
        "users_ou": os.environ.get("users_ou"),
        "groups_ou": os.environ.get("groups_ou"),
        "sudoers_group_name": os.environ.get("sudoers_group_name"),
        "computers_ou": os.environ.get("computers_ou"),
        "domain_tls_certificate_secret_arn": os.environ.get(
            "domain_tls_certificate_secret_arn"
        ),
        "enable_ldap_id_mapping": os.environ.get("enable_ldap_id_mapping"),
        "disable_ad_join": os.environ.get("disable_ad_join"),
        "root_user_dn_secret_arn": os.environ.get("root_user_dn_secret_arn"),
        # Shared Storage details
        "existing_home_fs_id": os.environ.get("existing_home_fs_id"),
        # Custom domain details
        "webapp_custom_dns_name": os.environ.get("webapp_custom_dns_name"),
        "acm_certificate_arn": os.environ.get("acm_certificate_arn"),
        "vdi_custom_dns_name": os.environ.get("vdi_custom_dns_name"),
        "certificate_secret_arn": os.environ.get("certificate_secret_arn"),
        "private_key_secret_arn": os.environ.get("private_key_secret_arn"),
        #  Internet Proxy details
        "http_proxy": os.environ.get("http_proxy_value"),
        "https_proxy": os.environ.get("https_proxy_value"),
        "no_proxy": os.environ.get("no_proxy_value"),
    }
    return input_parameters
