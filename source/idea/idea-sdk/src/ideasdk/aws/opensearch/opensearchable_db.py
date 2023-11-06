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
from abc import abstractmethod
from logging import Logger
from typing import Dict, Optional
import json

from ideadatamodel import SocaListingPayload, SocaSortOrder, SocaSortBy
from ideasdk.aws.opensearch.aws_opensearch_client import AwsOpenSearchClient
from ideasdk.aws.opensearch.opensearch_filters import FreeTextFilter, TermFilter, RangeFilter, SortOrder, SortFilter
from ideasdk.context import SocaContext
from ideasdk.utils import Utils


class OpenSearchableDB:
    FREE_TEXT_FILTER_KEY = '$all'

    def __init__(self, context: SocaContext, logger: Logger, term_filter_map: Optional[Dict] = None, date_range_filter_map: Optional[Dict] = None, default_page_size: int = 10, free_text_search_support: bool = True):
        self.context = context
        self._logger = logger
        self._term_filter_map = term_filter_map
        self._date_range_filter_map = date_range_filter_map
        self._default_page_size = default_page_size
        self._os_client = AwsOpenSearchClient(self.context)
        self._free_text_search_support = free_text_search_support

    def list_from_opensearch(self, options: SocaListingPayload):
        # documentation to read - https://opensearch.org/docs/latest/opensearch/query-dsl/

        term_filters = []
        free_text_filter_value = None
        if Utils.is_not_empty(options.filters):
            for listing_filter in options.filters:

                if Utils.is_empty(listing_filter.key):
                    continue

                if Utils.is_empty(listing_filter.value):
                    continue

                if listing_filter.key == self.FREE_TEXT_FILTER_KEY:
                    free_text_filter_value = listing_filter.value.lower()
                    continue

                if listing_filter.key not in self._term_filter_map.keys():
                    continue

                term_filters.append(TermFilter(
                    key=self._term_filter_map[listing_filter.key],
                    value=listing_filter.value
                ))

        range_filter = None
        if Utils.is_not_empty(options.date_range) and Utils.is_not_empty(self._date_range_filter_map):
            date_range = options.date_range
            if date_range.key in self._date_range_filter_map.keys():
                range_filter = RangeFilter(
                    key=self._date_range_filter_map[date_range.key],
                    start=f'{Utils.to_milliseconds(date_range.start)}',
                    end=f'{Utils.to_milliseconds(date_range.end)}'
                )

        if Utils.is_empty(options.sort_by):
            options.sort_by = self.get_default_sort()

        sort_filter = SortFilter(
            key=options.sort_by.key,
            order=SortOrder.DESC if options.sort_by.order == SocaSortOrder.DESC else SortOrder.ASC
        )

        response = self._os_client.search(
            index=self.get_index_name(),
            term_filters=term_filters,
            range_filter=range_filter,
            sort_filter=sort_filter,
            start_from=0,
            size=None,
        )

        response_hits = (response.get('hits') or {}).get('hits')

        if response_hits and free_text_filter_value:
            free_text_filtered_responses = []
            for hit in response_hits:
                json_dump = json.dumps(hit.get('_source')).lower()

                if free_text_filter_value in json_dump:
                    free_text_filtered_responses.append(hit)

            response['hits']['hits'] = free_text_filtered_responses

        return response

    @abstractmethod
    def get_index_name(self) -> str:
        ...

    @abstractmethod
    def get_default_sort(self) -> SocaSortBy:
        ...
