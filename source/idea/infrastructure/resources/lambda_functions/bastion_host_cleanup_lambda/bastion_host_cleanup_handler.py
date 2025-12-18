#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict

import boto3
from res.utils.custom_resource_utils import (  # type: ignore
    CustomResourceResponse,
    send_response,
)

TAG_NAME = "res:EnvironmentName"
BASTION_HOST_INSTANCE_ID = "bastion-host.instance_id"
BASTION_HOST_HOSTNAME = "bastion-host.hostname"
BASTION_HOST_HOSTED_ZONE_ID = "cluster.route53.private_hosted_zone_id"
BASTION_HOST_HOSTED_ZONE_NAME = "cluster.route53.private_hosted_zone_name"


def handle_bastion_host_delete(event: Dict[str, Any], _: Any) -> None:
    cr_response = CustomResourceResponse(
        Status="SUCCESS",
        Reason="SUCCESS",
        PhysicalResourceId=event["LogicalResourceId"],
        StackId=event["StackId"],
        RequestId=event["RequestId"],
        LogicalResourceId=event["LogicalResourceId"],
    )
    properties = event.get("ResourceProperties", {})
    cluster_name = properties.get("cluster_name")
    CLUSTER_SETTINGS_TABLE = f"{cluster_name}.cluster-settings"

    if event["RequestType"] == "Delete":
        print("Received event for bastion host deletion")
        # Get the instance_id from the cluster-settings DynamoDB table
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(CLUSTER_SETTINGS_TABLE)
        response = table.get_item(Key={"key": BASTION_HOST_INSTANCE_ID})

        if "Item" not in response or not response["Item"].get("value"):
            # Nothing to delete
            send_response(url=event["ResponseURL"], response=cr_response)
            return

        instance_id = response["Item"].get("value")

        print(f"Retrieved instance ID {instance_id} from cluster-settings table")

        ec2 = boto3.client("ec2")

        # Terminate EC2 instance
        ec2.terminate_instances(InstanceIds=[instance_id])
        print(f"Successfully terminated EC2 instance (ID: {instance_id})")

        # Wait for the instance to be terminated
        waiter = ec2.get_waiter("instance_terminated")
        waiter.wait(InstanceIds=[instance_id])
        print(f"EC2 instance (ID: {instance_id}) has been fully terminated")

        # Delete Route53 "A" record
        route53 = boto3.client("route53")

        # Retrieve necessary information from DynamoDB

        hostname = (
            table.get_item(Key={"key": BASTION_HOST_HOSTNAME})
            .get("Item", {})
            .get("value", "")
        )
        private_hosted_zone_id = (
            table.get_item(Key={"key": BASTION_HOST_HOSTED_ZONE_ID})
            .get("Item", {})
            .get("value", "")
        )
        private_hosted_zone_name = (
            table.get_item(Key={"key": BASTION_HOST_HOSTED_ZONE_NAME})
            .get("Item", {})
            .get("value", "")
        )

        if not all([hostname, private_hosted_zone_id, private_hosted_zone_name]):
            raise ValueError(
                "Missing required Route53 information in cluster-settings table"
            )

        # Get the current record details
        record_name = f"{hostname}.{private_hosted_zone_name}"
        response = route53.list_resource_record_sets(
            HostedZoneId=private_hosted_zone_id,
            StartRecordName=record_name,
            StartRecordType="A",
            MaxItems="1",
        )

        if response["ResourceRecordSets"]:
            current_record = response["ResourceRecordSets"][0]
            if (
                current_record["Name"].rstrip(".") == record_name.rstrip(".")
                and current_record["Type"] == "A"
            ):

                # Delete the record
                change_batch = {
                    "Changes": [
                        {
                            "Action": "DELETE",
                            "ResourceRecordSet": {
                                "Name": current_record["Name"],
                                "Type": current_record["Type"],
                                "TTL": current_record["TTL"],
                                "ResourceRecords": current_record["ResourceRecords"],
                            },
                        }
                    ]
                }

                route53.change_resource_record_sets(
                    HostedZoneId=private_hosted_zone_id, ChangeBatch=change_batch
                )
        print(
            f"Successfully deleted Route53 'A' record for {hostname}.{private_hosted_zone_name}"
        )
    send_response(url=event["ResponseURL"], response=cr_response)
