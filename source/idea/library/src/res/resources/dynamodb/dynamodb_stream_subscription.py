#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import json
import os
import random
import threading
import time
import traceback
from logging import Logger
from typing import Any, Dict, List

import boto3
import botocore.exceptions
from boto3.dynamodb.types import TypeDeserializer
from res.resources.dynamodb.dynamodb_stream_subscriber import IDynamoDBStreamSubscriber

SHARD_ITERATOR_INITIALIZER_INTERVAL = (10, 30)
SHARD_PROCESSOR_INTERVAL = (10, 30)


class DynamoDBStreamSubscription:
    """
    Create subscription for a DynamoDB Stream and Publish updates via DynamoDBStreamSubscriber protocol
    """

    def __init__(
        self,
        table_name: str,
        table_kinesis_stream_name: str,
        stream_subscriber: IDynamoDBStreamSubscriber = None,
        logger=None,
    ) -> None:
        self.stream_subscribers = [stream_subscriber] if stream_subscriber else []
        self.table_name = table_name
        self.table_kinesis_stream_name = table_kinesis_stream_name
        self.logger = logger

        self.ddb_type_deserializer = TypeDeserializer()

        self._shard_iterator_lock = threading.RLock()
        self._exit = threading.Event()
        self.shard_iterators_map: Dict[str, str] = {}
        self.shard_initializer_thread = threading.Thread(
            name=f"{self.table_name}.shard-iterator-initializer",
            target=self.shard_iterator_initializer,
        )
        self.shard_initializer_thread.start()
        self.shard_processor_thread = threading.Thread(
            name=f"{self.table_name}.shard-processor", target=self.shard_processor
        )
        self.shard_processor_thread.start()

    def set_logger(self, logger):
        self.logger = logger

    def subscribe(self, stream_subscriber: IDynamoDBStreamSubscriber):
        if stream_subscriber in self.stream_subscribers:
            self.log_info(f"{stream_subscriber.subscriber_name} already subscribed")
            return

        self.stream_subscribers.append(stream_subscriber)

    def log_info(self, message: str) -> None:
        if self.logger is not None:
            self.logger.info(message)
        else:
            print(message)

    def log_exception(self, message: str) -> None:
        if self.logger is not None:
            self.logger.exception(message)
        else:
            print(message)
            traceback.print_exc()

    def log_debug(self, message: str) -> None:
        if self.logger is not None:
            self.logger.debug(message)

    def shard_iterator_initializer(self) -> None:
        """
        for a given dynamodb stream, find all available shards and initialize the shard iterator.
        a shard can be added or closed and this operation should be performed periodically.
        a clean-up operation is performed for all closed shards. a shard considered is closed, the NextShardIterator returns null value in GetRecords response.
        :return:
        """
        while not self._exit.is_set():
            kinesis_client = boto3.client(service_name="kinesis")
            try:
                with self._shard_iterator_lock:
                    list_shards_result = kinesis_client.list_shards(
                        StreamName=self.table_kinesis_stream_name
                    )
                    shards = list_shards_result.get("Shards", [])
                    for shard in shards:
                        shard_id = shard["ShardId"]
                        shard_iterator = self.shard_iterators_map.get(shard_id)
                        if shard_iterator is None:
                            success = False
                            while not success:
                                try:
                                    get_shard_iterator_result = (
                                        kinesis_client.get_shard_iterator(
                                            StreamName=self.table_kinesis_stream_name,
                                            ShardId=shard_id,
                                            ShardIteratorType="LATEST",
                                        )
                                    )
                                    self.shard_iterators_map[shard_id] = (
                                        get_shard_iterator_result["ShardIterator"]
                                    )
                                    success = True
                                except botocore.exceptions.ClientError as e:
                                    if (
                                        e.response["Error"]["Code"]
                                        == "ProvisionedThroughputExceededException"
                                    ):
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
                self.log_exception(
                    f"failed to initialize {self.table_name} shard iterator: {e}"
                )
            finally:
                self._exit.wait(random.randint(*SHARD_ITERATOR_INITIALIZER_INTERVAL))

    def shard_processor(self) -> None:
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
                            kinesis_client = boto3.client(service_name="kinesis")
                            try:
                                get_records_result = kinesis_client.get_records(
                                    ShardIterator=next_shard_iterator, Limit=1000
                                )
                            except botocore.exceptions.ClientError as e:
                                if (
                                    e.response["Error"]["Code"]
                                    == "ProvisionedThroughputExceededException"
                                ):
                                    time.sleep(1)
                                    continue
                                elif e.response["Error"]["Code"] in (
                                    "ExpiredIteratorException",
                                    "TrimmedDataAccessException",
                                ):
                                    next_shard_iterator = None
                                    break
                                else:
                                    raise e

                            # when the shard is closed, next shard iterator will be None
                            next_shard_iterator = get_records_result.get(
                                "NextShardIterator"
                            )
                            # records can be an empty set, even when NextShardIterator is not None as the shard is not closed yet.
                            records = get_records_result.get("Records", [])

                            if len(records) > 0:
                                self.log_info(
                                    f"{shard_id} - got {len(records)} records"
                                )

                            for record in records:
                                record_data = json.loads(record["Data"])
                                try:
                                    handle_record_data(
                                        record_data,
                                        self.ddb_type_deserializer,
                                        self.stream_subscribers,
                                        self.logger,
                                    )
                                except Exception as e:
                                    self.log_exception(
                                        f"failed to process {self.table_name} stream update: {e}, record: {record_data}"
                                    )

                            if len(records) == 0:
                                break
                            else:
                                time.sleep(1)

                        self.shard_iterators_map[shard_id] = next_shard_iterator

            except Exception as e:
                self.log_exception(f"failed to process {self.table_name} update: {e}")
            finally:
                # since each shard has polling limit of 5 per second, ensure polling intervals are spread out across all applications
                self._exit.wait(random.randint(*SHARD_PROCESSOR_INTERVAL))

    def stop(self) -> None:
        self._exit.set()
        self.shard_initializer_thread.join()
        self.shard_processor_thread.join()


def handle_record_data(
    record_data: Dict[str, Any],
    ddb_type_deserializer: TypeDeserializer,
    subscribers: List[IDynamoDBStreamSubscriber],
    logger: Logger,
) -> None:
    event_name = record_data["eventName"]
    if event_name == "INSERT":
        logger.debug(f"Received INSERT event: %s", record_data)

        config_entry_raw = record_data["dynamodb"]["NewImage"]
        config_entry = {
            k: ddb_type_deserializer.deserialize(v) for k, v in config_entry_raw.items()
        }
        for subscriber in subscribers:
            if subscriber.is_entry_monitored(config_entry):
                subscriber.on_create(config_entry)
    elif event_name == "MODIFY":
        logger.debug(f"Received MODIFY event: %s", record_data)

        old_config_entry_raw = record_data["dynamodb"]["OldImage"]
        old_config_entry = {
            k: ddb_type_deserializer.deserialize(v)
            for k, v in old_config_entry_raw.items()
        }
        new_config_entry_raw = record_data["dynamodb"]["NewImage"]
        new_config_entry = {
            k: ddb_type_deserializer.deserialize(v)
            for k, v in new_config_entry_raw.items()
        }
        for subscriber in subscribers:
            if subscriber.is_entry_monitored(old_config_entry):
                subscriber.on_update(old_config_entry, new_config_entry)
    elif event_name == "REMOVE":
        logger.debug(f"Received REMOVE event: %s", record_data)

        config_entry_raw = record_data["dynamodb"]["OldImage"]
        config_entry = {
            k: ddb_type_deserializer.deserialize(v) for k, v in config_entry_raw.items()
        }
        for subscriber in subscribers:
            if subscriber.is_entry_monitored(config_entry):
                subscriber.on_delete(config_entry)
