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

from ideasdk.protocols import \
    SocaMetricsServiceProtocol, \
    SocaMetricsAccumulator, \
    CacheProviderProtocol, \
    SocaCacheProtocol, CacheTTL

from typing import List, Dict, Optional, Hashable, Any
from cacheout import Cache


class EmptyMetricsService(SocaMetricsServiceProtocol):

    def register_accumulator(self, accumulator: SocaMetricsAccumulator):
        pass

    def publish(self, metric_data: List[Dict]):
        pass

    def start(self):
        pass

    def stop(self):
        pass


class EmptySocaCache(SocaCacheProtocol):

    @property
    def name(self) -> str:
        return ''

    @property
    def size_in_bytes(self) -> int:
        return 0

    @property
    def size(self) -> int:
        return 0

    def get(self, key: Hashable, default: Any = None) -> Any:
        return None

    def set(self, key: Hashable, value: Any, ttl: Optional[CacheTTL] = None) -> None:
        return None

    @property
    def cache_backend(self) -> Optional[Cache]:
        return None


class EmptyCacheProvider(CacheProviderProtocol):

    def __init__(self):
        self._cache = EmptySocaCache()

    def long_term(self) -> SocaCacheProtocol:
        return self._cache

    def short_term(self) -> SocaCacheProtocol:
        return self._cache

    def reload(self, name: str = None) -> SocaCacheProtocol:
        pass
