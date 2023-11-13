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

from ideadatamodel import constants
from fastcounter import FastWriteCounter as Counter
from typing import Optional


class FastWriteCounter:
    """
    Fast Write Counter
    thread safe - non-blocking write counter

    > these will be called in a high velocity from multiple threads, and we need a good increment strategy
    without a performance hit
    > we cannot use this on a python implementation that not based on C

    > the implementation uses GIL and protects concurrent access to the internal data structure in C,
    so there's no need for us to lock anything.

    see: https://julien.danjou.info/atomic-lock-free-counters-in-python/ for more details
    """

    def __init__(self, name: str):
        self._name = name
        self._prev_count = 0
        self._count = Counter()

    @property
    def name(self):
        return self._name

    def increment(self, num_steps=1):
        self._count.increment(num_steps)

    def get(self) -> Optional[int]:
        """
        get has a read penalty. should not be call get at a high velocity
        :return: returns None if the count has not changed, otherwise returns the counter value.
        """
        count = self._count.value

        if count == self._prev_count:
            return None

        delta_count = count - self._prev_count
        self._prev_count = count
        return delta_count
