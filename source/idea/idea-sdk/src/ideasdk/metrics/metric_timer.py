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

import arrow


class MetricTimer:

    def __init__(self):
        self.start = arrow.utcnow()

    def elapsed(self):
        return arrow.utcnow() - self.start

    def elapsed_in_ms(self):
        return self.elapsed().total_seconds() * 1000

    def elapsed_in_seconds(self):
        return self.elapsed().total_seconds()
