#!/usr/bin/env python3
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
import boto3
import requests
import json
import argparse

from iam_auth import IAMAuth

def main():
    parser = argparse.ArgumentParser(description="Fetch AWS temporary credentials using IAM authorization")
    parser.add_argument("--filesystem-name", "-n", required=True, help="Name of the filesystem")
    parser.add_argument("--api-url", "-u", required=True, help="URL of the API endpoint")
    args = parser.parse_args()

    session = requests.Session()
    session.auth = IAMAuth(boto3_session=boto3.Session(profile_name="default"))

    query_params = {
        "filesystemName": args.filesystem_name
    }
    response = session.get(args.api_url, params=query_params)
    response_json = response.json()

    print(json.dumps(response_json, indent=4))


if __name__ == "__main__":
    main()
