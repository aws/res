#!/usr/bin/env python3

import sys
import boto3
import requests
import json
import argparse
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.compat import (parse_qsl, urlparse)


class IAMAuth(requests.auth.AuthBase):
    def __init__(self, boto3_session=None, service_name='execute-api'):
        self.boto3_session = boto3_session or boto3.Session(profile_name='default')
        self.sigv4 = SigV4Auth(
            credentials=self.boto3_session.get_credentials(),
            service_name=service_name,
            region_name=self.boto3_session.region_name,
        )

    def __call__(self, request):
        # Parse request URL
        url = urlparse(request.url)

        # Prepare AWS request
        awsrequest = AWSRequest(
            method=request.method,
            url=f'{url.scheme}://{url.netloc}{url.path}',
            data=request.body,
            params=dict(parse_qsl(url.query)),
        )

        # Sign request
        self.sigv4.add_auth(awsrequest)

        # Return prepared request
        return awsrequest.prepare()


def main():
    parser = argparse.ArgumentParser(description="Fetch AWS temporary credentials using IAM authorization")
    parser.add_argument("--filesystem-name", "-n", required=True, help="Name of the filesystem")
    parser.add_argument("--api-url", "-u", required=True, help="URL of the API endpoint")
    args = parser.parse_args()

    session = requests.Session()
    session.auth = IAMAuth()

    query_params = {
        "filesystemName": args.filesystem_name
    }
    response = session.get(args.api_url, params=query_params)
    response_json = response.json()

    print(json.dumps(response_json, indent=4))


if __name__ == "__main__":
    main()
