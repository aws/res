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

from ideasdk.config.soca_config import SocaConfig
from ideasdk.protocols import \
    SocaContextProtocol, \
    SocaCacheProtocol, \
    CacheProviderProtocol, \
    CacheTTL

import typing as t
from cacheout import CacheManager, LRUCache
import sys
import logging

CACHE_LONG_TERM = 'long_term'
CACHE_SHORT_TERM = 'short_term'


class SocaCache(SocaCacheProtocol):
    """
    This is a wrapper on top of LRUCache or any other cache backend

    the primary objective of this wrapper class is to enable caching API calls, even when caching is disabled.
    the benefit of this pattern is the code does not have to check if caching is enabled or cache client is null.

    additionally, we can add some central caching metrics or logging for instrumentation or debugging

    !! Important: outside the SDK, additional methods for caching must be exposed via SocaCache
    !! do not use, SocaCache.cache_backend.<method>

    """

    def __init__(self, context: SocaContextProtocol, logger: logging.Logger, name,
                 cache: LRUCache = None):
        self._name = name
        self._context = context
        self._logger = logger
        self._cache = cache

    @property
    def cache_backend(self) -> t.Optional[LRUCache]:
        return self._cache

    @property
    def name(self) -> str:
        return self._name

    @property
    def size_in_bytes(self) -> int:
        if not self._cache:
            return 0
        return sys.getsizeof(self._cache._cache)  # noqa

    @property
    def size(self) -> int:
        if not self._cache:
            return 0
        return self._cache.size()

    def get(self, key: t.Hashable, default: t.Any = None) -> t.Any:
        if self._cache is None:
            return None
        value = self._cache.get(key, default)
        if value is None:
            if self._logger.isEnabledFor(logging.DEBUG):
                self._logger.debug(f'({self._name}) miss -> {key}')
        return value

    def set(self, key: t.Hashable, value: t.Any, ttl: t.Optional[CacheTTL] = None) -> None:
        if self._cache is None:
            return None
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(f'({self._name}) set -> {key}')
        return self._cache.set(key, value, ttl)

    def delete(self, key: t.Hashable) -> int:
        if self._cache is None:
            return 0
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(f'({self._name}) delete -> {key}')
        return self._cache.delete(key)

    def publish_metrics(self):
        if self._cache is None:
            return


class CacheProvider(CacheProviderProtocol):
    def __init__(self, context: SocaContextProtocol, module_id: str):
        self._context = context
        self._logger = context.logger(name='cache_service')
        self.module_id = module_id
        self._cache_manager: t.Optional[CacheManager] = None
        self._soca_cache_clients: t.Dict[str, SocaCache] = {}
        self._initialize()

    def _config(self) -> SocaConfig:
        return self._context.config()

    def _is_cache_available(self, key) -> bool:
        cache = self._get_cache(key=key)
        return cache is not None

    def _get_cache(self, key) -> t.Optional[LRUCache]:
        if self._cache_manager is None:
            return None
        if key not in self._cache_manager:
            return None
        return self._cache_manager[key]

    def _init_client(self, key):
        cache = self._cache_manager[key]
        self._soca_cache_clients[key] = SocaCache(
            context=self._context,
            logger=self._logger,
            name=key,
            cache=cache
        )

    def _initialize(self):
        """
        this method initializes the cache manager and builds the _soca_cache_clients dict
        the goal if this method is to support CacheProvider initialization at:
            * start up
            * during hot reload

        special handling is required for supporting hot reload and hence the complexity
        we do not supporting adding new caches at runtime. new caches need new configuration entries,
            and updates to soca-sdk
        """

        settings = {}

        def build_or_configure(key: str, cache_settings_prefix: str):
            cache = self._get_cache(key=key)
            maxsize = self._context.config().get_int(f'{cache_settings_prefix}.max_size', default=1000)
            ttl = self._context.config().get_int(f'{cache_settings_prefix}.ttl_seconds', default=600)
            if cache is None:
                # initialize settings for brand new cache
                settings[key] = {
                    'maxsize': maxsize,
                    'ttl': ttl
                }
            else:
                # reconfigure the cache ttl and max size parameters if changed at runtime
                cache.configure(maxsize=maxsize, ttl=ttl)

        build_or_configure(key=CACHE_LONG_TERM, cache_settings_prefix=f'{self.module_id}.cache.long_term')
        build_or_configure(key=CACHE_SHORT_TERM, cache_settings_prefix=f'{self.module_id}.cache.short_term')

        if self._cache_manager is None and len(settings.keys()) > 0:
            self._cache_manager = CacheManager(
                settings=settings,
                cache_class=LRUCache
            )
            self._init_client(CACHE_LONG_TERM)
            self._init_client(CACHE_SHORT_TERM)

    def long_term(self) -> SocaCache:
        """
        long term cache should be used for objects that do not change over a long period of time.
        examples of these are infrastructure objects such as AWS Secrets, ALB Listener ARN, AWS Pricing etc.
        :return: SocaCache
        """
        return self._soca_cache_clients[CACHE_LONG_TERM]

    def short_term(self) -> SocaCache:
        return self._soca_cache_clients[CACHE_SHORT_TERM]

    @property
    def accumulator_id(self):
        return 'cache-metrics'

    def publish_metrics(self):
        for cache in self._soca_cache_clients.values():
            cache.publish_metrics()

    def _clear_all(self):
        if self._cache_manager is None:
            return
        self._cache_manager.clear_all()

    def reload(self, name: str = None):
        self._initialize()
