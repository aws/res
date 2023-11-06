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

import ideaclustermanager

from ideasdk.api import ApiInvocationContext, BaseAPI
from ideadatamodel.analytics import (
    OpenSearchQueryRequest,
    OpenSearchQueryResult
)
from ideadatamodel import exceptions
from ideasdk.utils import Utils


class AnalyticsAPI(BaseAPI):
    """
    Analytics API to query opensearch cluster.

    this is a stop-gap API and ideally, each module should implement their own version of Analytics API,
    scoped to the indices or aliases exposed by a particular module.

    any write or index settings apis must not be exposed via this class.
    an AnalyticsAdminAPI should be exposed with elevated access to enable such functionality.

    invocation simply checks if the invocation is authenticated (valid token)
    """

    def __init__(self, context: ideaclustermanager.AppContext):
        self.context = context

    def opensearch_query(self, context: ApiInvocationContext):
        """
        Send Raw ElasticSearch Query and Search Request
        """
        request = context.get_request_payload_as(OpenSearchQueryRequest)
        if Utils.is_empty(request.data):
            raise exceptions.invalid_params('data is required')

        result = self.context.analytics_service().os_client.os_client.search(
            **request.data
        )

        context.success(OpenSearchQueryResult(
            data=result
        ))

    def invoke(self, context: ApiInvocationContext):
        if not context.is_authenticated():
            raise exceptions.unauthorized_access()

        namespace = context.namespace
        if namespace == 'Analytics.OpenSearchQuery':
            self.opensearch_query(context)
