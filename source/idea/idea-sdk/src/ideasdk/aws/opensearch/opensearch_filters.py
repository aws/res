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

__all__ = (
    'TermFilter',
    'RangeFilter',
    'FreeTextFilter',
    'SortFilter',
    'SortOrder'
)

from enum import Enum
from typing import List, Union, Dict


class TermFilter:
    key: str
    value: List[str]

    def __init__(self, key: str, value: Union[str, List[str]]):
        self.key = key
        if isinstance(value, str):
            self.value = [value]
        else:
            self.value = value

    def get_term_filter(self) -> Dict:
        return {
            'terms': {
                self.key: self.value
            }
        }


class RangeFilter:
    key: str
    start: str
    end: str

    def __init__(self, key: str, start: str, end: str):
        self.key = key
        self.start = start
        self.end = end

    def get_range_filter(self) -> Dict:
        return {
            'range': {
                self.key: {
                    'gte': self.start,
                    'lt': self.end
                }
            }
        }


class FreeTextFilter:
    text: str

    def __init__(self, text: str):
        self.text = text

    def get_free_text_filter(self) -> Dict:
        return {
            'query_string': {
                "fields": [],
                "query": self.text
            }
        }


class SortOrder(str, Enum):
    ASC = 'asc'
    DESC = 'desc'


class SortFilter:
    key: str
    order: SortOrder

    def __init__(self, key: str, order: SortOrder):
        self.key = key
        self.order = order

    def get_sort_filter(self) -> str:
        return f'{self.key}:{self.order}'
