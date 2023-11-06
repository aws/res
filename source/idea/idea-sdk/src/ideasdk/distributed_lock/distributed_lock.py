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
from ideadatamodel.constants import SERVICE_ID_DISTRIBUTED_LOCK
from ideasdk.protocols import SocaContextProtocol, DistributedLockProtocol
from ideasdk.service import SocaService
from python_dynamodb_lock.python_dynamodb_lock import DynamoDBLockClient

import datetime
import time
import random
from threading import RLock


class DistributedLock(SocaService, DistributedLockProtocol):
    """
    Distributed Lock based on DynamoDB

    Refer to: https://python-dynamodb-lock.readthedocs.io/en/latest/index.html for more information.
    Python Library is based on the Java Implementation https://github.com/awslabs/amazon-dynamodb-lock-client from awslabs

    Primary use-case for Distributed Locks in IDEA is Leader Election.
    Individual Modules may use the DistributedLock functionality as deem fit.

    DistributedLock is automatically initialized by SocaContext if `options.enable_distributed_lock = True`
    """

    def __init__(self, context: SocaContextProtocol,
                 heartbeat_period=5,
                 safe_period=20,
                 lease_duration=30,
                 expiry_period=60*60,
                 heartbeat_tps=-1):
        """
        :param SocaContext context: Application Context
        :param int heartbeat_period: How often to update DynamoDB to note that the
                instance is still running. It is recommended to make this at least 4 times smaller
                than the leaseDuration. Defaults to 5 seconds.
        :param int safe_period: How long is it okay to go without a heartbeat before
                considering a lock to be in "danger". Defaults to 20 seconds.
        :param int lease_duration: The length of time that the lease for the lock
                will be granted for. i.e. if there is no heartbeat for this period of time, then
                the lock will be considered as expired. Defaults to 30 seconds.
        :param int expiry_period: The fallback expiry timestamp to allow DynamoDB
                to cleanup old locks after a server crash. This value should be significantly larger
                than the _lease_duration to ensure that clock-skew etc. are not an issue. Defaults
                to 1 hour.
        :param int heartbeat_tps: The number of heartbeats to execute per second (per node) - this
                will have direct correlation to DynamoDB provisioned throughput for writes. If set
                to -1, the client will distribute the heartbeat calls evenly over the _heartbeat_period
                - which uses lower throughput for smaller number of locks. However, if you want a more
                deterministic heartbeat-call-rate, then specify an explicit TPS value. Defaults to -1.
        """
        super().__init__(context)
        self.context = context
        self.logger = context.logger('distributed-lock')

        self._initialize_distributed_lock_table()

        self._lock_client = DynamoDBLockClient(
            dynamodb_resource=context.aws().dynamodb_table(),
            table_name=self._get_table_name(),
            partition_key_name='lock_key',
            sort_key_name='sort_key',
            ttl_attribute_name='expiry_time',
            heartbeat_period=datetime.timedelta(seconds=heartbeat_period),
            safe_period=datetime.timedelta(seconds=safe_period),
            lease_duration=datetime.timedelta(seconds=lease_duration),
            expiry_period=datetime.timedelta(seconds=expiry_period),
            heartbeat_tps=heartbeat_tps
        )

        self._lock = RLock()
        self._active_locks = {}

    def service_id(self) -> str:
        return SERVICE_ID_DISTRIBUTED_LOCK

    def _get_table_name(self) -> str:
        return f'{self.context.cluster_name()}.{self.context.module_id()}.distributed-lock'

    def _initialize_distributed_lock_table(self):
        exists = self.context.aws_util().dynamodb_check_table_exists(self._get_table_name())
        if not exists:
            # wait for random duration to avoid race condition for table creation with other nodes
            time.sleep(random.randint(0, 5))

        self.context.aws_util().dynamodb_create_table(
            create_table_request={
                'TableName': self._get_table_name(),
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'lock_key',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'sort_key',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'lock_key',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'sort_key',
                        'KeyType': 'RANGE'
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            },
            wait=True,
            ttl=True,
            ttl_attribute_name='expiry_time'
        )

    def acquire(self, key: str):
        acquired_lock = self._lock_client.acquire_lock(partition_key=key)
        with self._lock:
            self._active_locks[key] = acquired_lock

    def release(self, key: str):
        if key not in self._active_locks:
            return
        self._lock_client.release_lock(
            lock=self._active_locks[key],
            best_effort=True
        )
        with self._lock:
            del self._active_locks[key]

    def start(self):
        pass

    def stop(self):
        self.logger.info('stopping distributed lock ...')
        if self._lock_client is not None:
            for key in self._active_locks:
                self.release(key)
            self._lock_client.close(release_locks=True)
