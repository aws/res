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

import time

import res.exceptions as exceptions  # type: ignore
from res.clients.ad_sync import ad_sync_client  # type: ignore


def ad_sync() -> None:
    try:
        ad_sync_client.start_ad_sync()
    except exceptions.ADSyncInProcess:
        # AD Sync may have been triggered by the scheduler Lambda or Cluster Manager and is still in progress
        pass

    # Wait for the AD sync to complete as this is an async call.
    time.sleep(90)
