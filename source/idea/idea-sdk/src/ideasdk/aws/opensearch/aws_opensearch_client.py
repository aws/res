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
import opensearchpy

from ideasdk.aws.opensearch.opensearch_filters import (
    TermFilter,
    RangeFilter,
    FreeTextFilter,
    SortFilter
)
from ideasdk.protocols import SocaContextProtocol

from typing import Optional, Dict, List
from opensearchpy import OpenSearch, helpers

from ideasdk.utils import Utils


class AwsOpenSearchClient:
    def __init__(self, context: SocaContextProtocol):
        self.context = context
        self._logger = context.logger('opensearch-client')

        domain_endpoint = self.context.config().get_string('analytics.opensearch.domain_endpoint', required=True)
        if not domain_endpoint.startswith('https://'):
            domain_endpoint = f'https://{domain_endpoint}'

        self.os_client = OpenSearch(
            hosts=[domain_endpoint],
            port=443,
            use_ssl=True,
            verify_certs=True
        )

    def add_index_entry(self, index_name: str, doc_id: str, body: str, **kwargs):
        timeout = kwargs.get('timeout', '10s')
        response = self.os_client.index(
            index=index_name,
            id=doc_id,
            body=body,
            timeout=timeout
        )
        return response['result'] == 'created'

    def bulk_index(self, index_name: str, docs: Dict[str, Dict], **kwargs):

        items = []

        for doc_id, doc in docs.items():
            items.append({
                '_index': index_name,
                '_id': doc_id,
                '_source': doc
            })

        helpers.bulk(
            client=self.os_client,
            actions=items
        )

        return True

    def search(self, index: str, term_filters: Optional[List[TermFilter]] = None, range_filter: Optional[RangeFilter] = None, free_text_filter: Optional[FreeTextFilter] = None, sort_filter: Optional[SortFilter] = None, size: Optional[int] = None, start_from: Optional[int] = None, source: bool = True) -> dict:
        query = {"bool": {}}
        if Utils.is_not_empty(term_filters):
            query["bool"]["must"] = Utils.get_value_as_list("must", query["bool"], default=[])
            for term_filter in term_filters:
                query["bool"]["must"].append(term_filter.get_term_filter())

        if Utils.is_not_empty(free_text_filter):
            query["bool"]["must"] = Utils.get_value_as_list("must", query["bool"], default=[])
            query["bool"]["must"].append(free_text_filter.get_free_text_filter())

        if Utils.is_not_empty(range_filter):
            query["bool"]["filter"] = Utils.get_value_as_list("filter", query["bool"], default=[])
            query["bool"]["filter"].append(range_filter.get_range_filter())

        sort_by = None
        if Utils.is_not_empty(sort_filter):
            sort_by = sort_filter.get_sort_filter()

        return self._search(
            index=index,
            body={'query': query},
            sort_by=sort_by,
            size=size,
            start_from=start_from,
            source=source
        )

    def _search(self, index: str, body: dict, sort_by: Optional[str] = None, size: Optional[int] = None, start_from: Optional[int] = None, source: bool = True) -> dict:
        try:
            result = self.os_client.search(
                index=index,
                body=body,
                sort=sort_by,
                size=size,
                from_=start_from,
                _source=source
            )
        except opensearchpy.exceptions.NotFoundError:
            # if index does not exist, return False
            # this allows new index to be created automatically
            return {}
        return result

    def exists(self, index: str, body: dict):
        result = self._search(index, body, source=False)
        return Utils.get_value_as_int('value', Utils.get_value_as_dict('total', Utils.get_value_as_dict('hits', result, {}), {}), 0) > 0

    def get_template(self, name: str) -> Optional[Dict]:
        try:
            return self.os_client.indices.get_template(name=name)
        except opensearchpy.exceptions.NotFoundError:
            return None

    def delete_alias_and_index(self, name: str):
        try:
            response = self.os_client.indices.get_alias(name=name)
        except opensearchpy.exceptions.NotFoundError as _:
            response = None

        if Utils.is_empty(response):
            return

        for index_name in response:
            try:
                self.os_client.indices.delete_alias(
                    index=index_name,
                    name=name
                )
            except opensearchpy.exceptions.NotFoundError as _:
                pass
            self._logger.warning(f'Alias: {name} deleted ...')
            self.delete_index(index_name)

    def delete_index(self, name: str):
        try:
            self.os_client.indices.delete(
                index=name
            )
        except opensearchpy.exceptions.NotFoundError as _:
            pass
        self._logger.warning(f'Index: {name} deleted ...')

    def delete_template(self, name: str):
        try:
            self.os_client.indices.delete_template(name=name)
        except opensearchpy.exceptions.NotFoundError as _:
            pass
        self._logger.warning(f'Template: {name} deleted ...')

    def put_template(self, name: str, body: Dict) -> Dict:
        return self.os_client.indices.put_template(name=name, body=body)
