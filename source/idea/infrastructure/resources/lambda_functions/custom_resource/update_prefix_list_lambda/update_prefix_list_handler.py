#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any, Dict

import boto3
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Dict[str, Any]) -> None:
    """
    Check and add new IP addresses to the prefix list
    """
    resource_properties = event.get("ResourceProperties", {})
    prefix_list_id = resource_properties["prefix_list_id"]
    add_entries = resource_properties.get("add_entries", [])

    response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event.get("LogicalResourceId", ""),
        StackId=event.get("StackId", ""),
        RequestId=event.get("RequestId", ""),
        LogicalResourceId=event.get("LogicalResourceId", ""),
        Data={},
    )

    try:
        ec2_client = boto3.client("ec2")

        if event["RequestType"] == "Update" or event["RequestType"] == "Delete":
            # Remove IP addresses that were added to the cluster prefix list
            old_properties = (
                event["OldResourceProperties"]
                if event["RequestType"] == "Update"
                else event["ResourceProperties"]
            )
            old_prefix_list_id = old_properties["prefix_list_id"]
            remove_entries = old_properties.get("add_entries", [])

            if len(remove_entries) > 0:
                for remove_entry in remove_entries:
                    logger.info(
                        f"Removing entry from cluster prefix list: {remove_entry}"
                    )

                ec2_client.modify_managed_prefix_list(
                    RemoveEntries=[
                        {"Cidr": remove_entry["Cidr"]}
                        for remove_entry in remove_entries
                    ],
                    PrefixListId=old_prefix_list_id,
                    CurrentVersion=get_prefix_list_version(old_prefix_list_id),
                )
            else:
                logger.info("no entries to remove. skip.")

        if event["RequestType"] != "Delete":
            add_entries_map = {}
            for entry in add_entries:
                cidr = entry["Cidr"]
                add_entries_map[cidr] = entry

            # find all existing entries and check if any entries already exist.
            prefix_list_paginator = ec2_client.get_paginator(
                "get_managed_prefix_list_entries"
            )
            prefix_list_iterator = prefix_list_paginator.paginate(
                PrefixListId=prefix_list_id
            )
            for prefix_list in prefix_list_iterator:
                cidr_entries = prefix_list.get("Entries", [])
                for cidr_entry in cidr_entries:
                    cidr = cidr_entry["Cidr"]
                    if cidr in add_entries_map:
                        del add_entries_map[cidr]

            add_entries = list(add_entries_map.values())

            if len(add_entries) > 0:
                for entry in add_entries:
                    logger.info(f"adding new entry to cluster prefix list: {entry}")

                ec2_client.modify_managed_prefix_list(
                    AddEntries=add_entries,
                    PrefixListId=prefix_list_id,
                    CurrentVersion=get_prefix_list_version(prefix_list_id),
                )
            else:
                logger.info("no new entries to add. skip.")

    except Exception as e:
        error_message = f"failed to update cluster prefix list: {e}"
        response["Status"] = "FAILED"
        response["Reason"] = error_message

        logging.exception(error_message)

    finally:
        send_response(url=event["ResponseURL"], response=response)


def get_prefix_list_version(prefix_list_id: str) -> Any:
    ec2_client = boto3.client("ec2")
    describe_result = ec2_client.describe_managed_prefix_lists(
        PrefixListIds=[prefix_list_id]
    )
    prefix_list_info = describe_result["PrefixLists"][0]
    return prefix_list_info["Version"]
