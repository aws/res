#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the 'License'). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from idea_lambda_commons import HttpClient, CfnResponse, CfnResponseStatus
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PHYSICAL_RESOURCE_ID = 'cluster-prefix-list'


def handler(event: dict, context):
    """
    Check and add new IP addresses to Cluster Prefix List
    Will not remove IP addresses from the cluster prefix list.
    """
    client = HttpClient()
    try:
        logging.info(f'ReceivedEvent: {event}')

        request_type = event.get('RequestType', None)
        if request_type == 'Delete':
            client.send_cfn_response(CfnResponse(
                context=context,
                event=event,
                status=CfnResponseStatus.SUCCESS,
                data={},
                physical_resource_id=PHYSICAL_RESOURCE_ID
            ))
            return

        resource_properties = event.get('ResourceProperties', {})
        prefix_list_id = resource_properties['prefix_list_id']
        add_entries = resource_properties.get('add_entries', [])

        add_entries_map = {}
        for entry in add_entries:
            cidr = entry['Cidr']
            add_entries_map[cidr] = entry

        ec2_client = boto3.client('ec2')

        # find all existing entries and check if any entries already exist.
        prefix_list_paginator = ec2_client.get_paginator('get_managed_prefix_list_entries')
        prefix_list_iterator = prefix_list_paginator.paginate(PrefixListId=prefix_list_id)
        for prefix_list in prefix_list_iterator:
            cidr_entries = prefix_list.get('Entries', [])
            for cidr_entry in cidr_entries:
                cidr = cidr_entry['Cidr']
                if cidr in add_entries_map:
                    del add_entries_map[cidr]

        add_entries = list(add_entries_map.values())

        if len(add_entries) > 0:
            for entry in add_entries:
                logger.info(f'adding new entry to cluster prefix list: {entry}')
            describe_result = ec2_client.describe_managed_prefix_lists(
                PrefixListIds=[prefix_list_id]
            )
            prefix_list_info = describe_result['PrefixLists'][0]
            version = prefix_list_info['Version']
            ec2_client.modify_managed_prefix_list(
                AddEntries=add_entries,
                PrefixListId=prefix_list_id,
                CurrentVersion=version
            )
        else:
            logger.info('no new entries to add. skip.')

        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.SUCCESS,
            data={},
            physical_resource_id=PHYSICAL_RESOURCE_ID
        ))

    except Exception as e:
        error_message = f'failed to update cluster prefix list: {e}'
        logging.exception(error_message)
        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.FAILED,
            data={},
            physical_resource_id=PHYSICAL_RESOURCE_ID,
            reason=error_message
        ))
    finally:
        client.destroy()
