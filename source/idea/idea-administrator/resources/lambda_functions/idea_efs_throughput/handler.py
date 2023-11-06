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

import json
import boto3
import datetime
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, _):
    cw_client = boto3.client('cloudwatch')
    efs_client = boto3.client('efs')
    message = json.loads(event['Records'][0]['Sns']['Message'])
    file_system_id = message['Trigger']['Dimensions'][0]['value']
    logger.info('FilesystemID: ' + file_system_id)

    now = datetime.datetime.now()
    start_time = now - datetime.timedelta(seconds=300)
    end_time = min(now, start_time + datetime.timedelta(seconds=300))
    response = cw_client.get_metric_statistics(Namespace='AWS/EFS', MetricName='BurstCreditBalance',
                                               Dimensions=[{'Name': 'FileSystemId', 'Value': file_system_id}],
                                               Period=60, StartTime=start_time, EndTime=end_time, Statistics=['Average'])
    efs_average_burst_credit_balance = response['Datapoints'][0]['Average']
    logger.info(f'EFS AverageBurstCreditBalance: {efs_average_burst_credit_balance}')

    response = efs_client.describe_file_systems(FileSystemId=file_system_id)
    throughput_mode = response['FileSystems'][0]['ThroughputMode']
    logger.info('EFS ThroughputMode: ' + str(throughput_mode))

    if efs_average_burst_credit_balance < int(os.environ['EFSBurstCreditLowThreshold']):
        # CreditBalance is less than LowThreshold --> Change to ProvisionedThroughput
        if throughput_mode == 'bursting':
            # Update file system to Provisioned
            efs_client.update_file_system(
                FileSystemId=file_system_id,
                ThroughputMode='provisioned',
                ProvisionedThroughputInMibps=5.0)
            logger.info('Updating EFS: ' + file_system_id + ' to Provisioned ThroughputMode with 5 MiB/sec')
    elif efs_average_burst_credit_balance > int(os.environ['EFSBurstCreditHighThreshold']):
        # CreditBalance is greater than HighThreshold --> Change to Bursting
        if throughput_mode == 'provisioned':
            # Update file system to Bursting
            efs_client.update_file_system(
                FileSystemId=file_system_id,
                ThroughputMode='bursting')
            logger.info('Updating EFS: ' + file_system_id + ' to Bursting ThroughputMode')
