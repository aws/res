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
from __future__ import print_function
import urllib3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class HttpClient:

    def __init__(self):
        self._http_client = urllib3.PoolManager()

    def http_post(self, *args, **kwargs):
        return self._http_client.request(*args, **kwargs)

    def send_cfn_response(self, response, log_response=True):

        json_response = response.build_response_payload()

        if log_response:
            logger.info(f'SendingResponse: {json_response}')
        else:
            logger.info('SendingResponse: REDACTED')

        try:
            response_url = response.response_url
            response = self._http_client.request('PUT', response_url, headers={
                'content-type': '',
                'content-length': str(len(json_response))
            }, body=json_response)
            logger.info(f'StatusCode: {response.status}')
        except Exception as e:
            logger.exception(f'SendResponseFailed, Error: {e}')

    def destroy(self):
        self._http_client.clear()
        self._http_client = None
