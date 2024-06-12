from ideasdk.utils import Utils
from typing import Dict, TypeVar

TRequest = TypeVar('TRequest')

def scan_db_records(request: TRequest, table) -> Dict:
    scan_request = {}

    cursor = request.cursor
    last_evaluated_key = None
    if Utils.is_not_empty(cursor):
        last_evaluated_key = Utils.from_json(Utils.base64_decode(cursor))
    if last_evaluated_key is not None:
        scan_request['ExclusiveStartKey'] = last_evaluated_key

    scan_filter = None
    if Utils.is_not_empty(request.filters):
        scan_filter = {}
        for filter_ in request.filters:
            if filter_.value == '$all':
                continue
            
            if filter_.eq is not None:
                scan_filter[filter_.key] = {
                    'AttributeValueList': [filter_.eq],
                    'ComparisonOperator': 'EQ'
                }
            if filter_.value is not None:
                scan_filter[filter_.key] = {
                    'AttributeValueList': [filter_.value],
                    'ComparisonOperator': 'CONTAINS'
                }
            if filter_.like is not None:
                scan_filter[filter_.key] = {
                    'AttributeValueList': [filter_.like],
                    'ComparisonOperator': 'CONTAINS'
                }
    if scan_filter is not None:
        scan_request['ScanFilter'] = scan_filter

    scan_result = table.scan(**scan_request)

    return scan_result