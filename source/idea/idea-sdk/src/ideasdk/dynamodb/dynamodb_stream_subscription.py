#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

from ideasdk.utils import Utils
from ideasdk.dynamodb.dynamodb_stream_subscriber import DynamoDBStreamSubscriber
import botocore.session
import botocore.exceptions
import os
from botocore.config import Config
from boto3.dynamodb.types import TypeDeserializer

import threading
from typing import Dict, Optional
import time
import random
import traceback

SHARD_ITERATOR_INITIALIZER_INTERVAL = (10, 30)
SHARD_PROCESSOR_INTERVAL = (10, 30)


class DynamoDBStreamSubscription:
    """
    Create subscription for a DynamoDB Stream and Publish updates via DynamoDBStreamSubscriber protocol
    """

    def __init__(self, stream_subscriber: DynamoDBStreamSubscriber, table_name: str, aws_region: str, aws_profile: Optional[str] = None, logger=None):

        self.stream_subscriber = stream_subscriber
        self.table_name = table_name
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self.logger = logger

        # todo @kulkary - vpc endpoint support
        self.boto_session = Utils.create_boto_session(self.aws_region, self.aws_profile)
        config = None
        https_proxy = os.environ.get('https_proxy')
        if not Utils.is_empty(https_proxy):
            proxy_definitions = {'https': https_proxy}
            config = Config(proxies=proxy_definitions)
        self.dynamodb_client = self.boto_session.client(service_name='dynamodb', region_name=self.aws_region)
        self.dynamodb_streams_client = self.boto_session.client(service_name='dynamodbstreams', region_name=self.aws_region, config=config)

        self.stream_arn: Optional[str] = None

        self.ddb_type_deserializer = TypeDeserializer()

        self._shard_iterator_lock = threading.RLock()
        self._exit = threading.Event()
        self.shard_iterators_map: Dict[str, str] = {}
        self.shard_initializer_thread = threading.Thread(name=f'{self.table_name}.shard-iterator-initializer', target=self.shard_iterator_initializer)
        self.shard_initializer_thread.start()
        self.shard_processor_thread = threading.Thread(name=f'{self.table_name}.shard-processor', target=self.shard_processor)
        self.shard_processor_thread.start()

    def set_logger(self, logger):
        self.logger = logger

    def log_info(self, message: str, logger=None):
        if logger is not None:
            logger.info(message)
        else:
            print(message)

    def log_exception(self, message: str, logger=None):
        if logger is not None:
            logger.exception(message)
        else:
            print(message)
            traceback.print_exc()

    def log_debug(self, message: str, logger=None):
        if logger is not None:
            logger.debug(message)

    def shard_iterator_initializer(self):
        """
        for a given dynamodb stream, find all available shards and initialize the shard iterator.
        a shard can be added or closed and this operation should be performed periodically.
        a clean-up operation is performed for all closed shards. a shard considered is closed, the NextShardIterator returns null value in GetRecords response.
        :return:
        """
        while not self._exit.is_set():
            try:
                with self._shard_iterator_lock:

                    # lazy initialize stream arn - once
                    if Utils.is_empty(self.stream_arn):
                        try:
                            describe_table_result = self.dynamodb_client.describe_table(TableName=self.table_name)
                            table = describe_table_result['Table']
                            self.stream_arn = table['LatestStreamArn']
                        except botocore.exceptions.ClientError as e:
                            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                                # table may not be created yet due to race condition in module deployments
                                continue
                            else:
                                raise e

                    describe_stream_result = self.dynamodb_streams_client.describe_stream(StreamArn=self.stream_arn)
                    shards = describe_stream_result['StreamDescription']['Shards']
                    for shard in shards:
                        shard_id = shard['ShardId']
                        shard_iterator = self.shard_iterators_map.get(shard_id)
                        if shard_iterator is None:
                            success = False
                            while not success:
                                try:
                                    get_shard_iterator_result = self.dynamodb_streams_client.get_shard_iterator(
                                        StreamArn=self.stream_arn,
                                        ShardId=shard_id,
                                        ShardIteratorType='LATEST'
                                    )
                                    self.shard_iterators_map[shard_id] = get_shard_iterator_result['ShardIterator']
                                    success = True
                                except botocore.exceptions.ClientError as e:
                                    if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                                        time.sleep(1)
                                        continue
                                    else:
                                        raise e

                    # clean up closed shards
                    shards_closed = []
                    for shard_id in self.shard_iterators_map.keys():
                        shard_iterator = self.shard_iterators_map.get(shard_id)
                        if shard_iterator is None:
                            shards_closed.append(shard_id)
                    for shard_id in shards_closed:
                        del self.shard_iterators_map[shard_id]

            except Exception as e:
                self.log_exception(f'failed to initialize {self.table_name} shard iterator: {e}', logger=self.logger)
            finally:
                self._exit.wait(random.randint(*SHARD_ITERATOR_INITIALIZER_INTERVAL))

    def shard_processor(self):
        """
        iterate over all shards periodically, and read all records from the latest shard iterator.
        the anticipated volume for configuration updates will be low to very low.

        since each application needs to read all configuration updates, all shards are read sequentially.
        :return:
        """
        while not self._exit.is_set():
            try:
                with self._shard_iterator_lock:

                    # randomize polling for shards so to avoid polling limit conflicts across servers
                    shard_ids = list(self.shard_iterators_map.keys())
                    random.shuffle(shard_ids)

                    for shard_id in shard_ids:

                        shard_iterator = self.shard_iterators_map[shard_id]

                        # shard is closed. skip
                        if shard_iterator is None:
                            continue

                        next_shard_iterator = shard_iterator
                        while True:
                            try:
                                get_records_result = self.dynamodb_streams_client.get_records(ShardIterator=next_shard_iterator, Limit=1000)
                            except botocore.exceptions.ClientError as e:
                                if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                                    time.sleep(1)
                                    continue
                                elif e.response['Error']['Code'] in ('ExpiredIteratorException', 'TrimmedDataAccessException'):
                                    next_shard_iterator = None
                                    break
                                else:
                                    raise e

                            # when the shard is closed, next shard iterator will be None
                            next_shard_iterator = get_records_result.get('NextShardIterator')
                            # records can be an empty set, even when NextShardIterator is not None as the shard is not closed yet.
                            records = get_records_result.get('Records', [])

                            if len(records) > 0:
                                self.log_info(f'{shard_id} - got {len(records)} records', logger=self.logger)

                            for record in records:
                                try:
                                    event_name = record['eventName']
                                    if event_name == 'INSERT':
                                        config_entry_raw = record['dynamodb']['NewImage']
                                        config_entry = {k: self.ddb_type_deserializer.deserialize(v) for k, v in config_entry_raw.items()}
                                        self.stream_subscriber.on_create(config_entry)
                                    elif event_name == 'MODIFY':
                                        old_config_entry_raw = record['dynamodb']['OldImage']
                                        old_config_entry = {k: self.ddb_type_deserializer.deserialize(v) for k, v in old_config_entry_raw.items()}
                                        new_config_entry_raw = record['dynamodb']['NewImage']
                                        new_config_entry = {k: self.ddb_type_deserializer.deserialize(v) for k, v in new_config_entry_raw.items()}
                                        self.stream_subscriber.on_update(old_config_entry, new_config_entry)
                                    elif event_name == 'REMOVE':
                                        config_entry_raw = record['dynamodb']['OldImage']
                                        config_entry = {k: self.ddb_type_deserializer.deserialize(v) for k, v in config_entry_raw.items()}
                                        self.stream_subscriber.on_delete(config_entry)
                                except Exception as e:
                                    self.log_exception(f'failed to process {self.table_name} stream update: {e}, record: {record}')

                            if len(records) == 0:
                                break
                            else:
                                time.sleep(1)

                        self.shard_iterators_map[shard_id] = next_shard_iterator

            except Exception as e:
                self.log_exception(f'failed to process {self.table_name} update: {e}')
            finally:
                # since each shard has polling limit of 5 per second, ensure polling intervals are spread out across all applications
                self._exit.wait(random.randint(*SHARD_PROCESSOR_INTERVAL))

    def stop(self):
        self._exit.set()
        self.shard_initializer_thread.join()
        self.shard_processor_thread.join()
