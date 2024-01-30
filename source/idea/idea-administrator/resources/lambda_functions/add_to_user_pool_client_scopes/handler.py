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

from idea_lambda_commons import HttpClient, CfnResponse, CfnResponseStatus
import boto3
import logging

PHYSICAL_RESOURCE_ID = 'user-pool-client'


def handler(event: dict, context):
    """
    Add OAuth scopes to an existing user pool client.
    """
    request_type = event.get('RequestType', None)
    resource_properties = event.get('ResourceProperties', {})
    cluster_name = resource_properties.get('cluster_name')
    module_id = resource_properties.get('module_id')
    stack_name = f'{cluster_name}-{module_id}'
    client_id_secrete_name = f'{stack_name}-client-id'
    user_pool_id = resource_properties.get('user_pool_id')
    o_auth_scopes_to_add = resource_properties.get('o_auth_scopes_to_add')
    client = HttpClient()

    if request_type == 'Delete':
        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.SUCCESS,
            data={},
            physical_resource_id=PHYSICAL_RESOURCE_ID
        ))
        return

    try:
        # Retrieve the client ID from Secrets Manager
        secretsmanager = boto3.client('secretsmanager')
        res = secretsmanager.get_secret_value(SecretId=client_id_secrete_name)
        client_id = res.get('SecretString', '')

        # Read the current configuration of the user pool client
        idp_client = boto3.client('cognito-idp')
        res = idp_client.describe_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_id
        )
        user_pool_client = res.get('UserPoolClient', {})
        user_pool_client.pop('ClientSecret', None)
        user_pool_client.pop('LastModifiedDate', None)
        user_pool_client.pop('CreationDate', None)

        allowed_o_auth_scopes = user_pool_client.get('AllowedOAuthScopes', [])
        allowed_o_auth_scopes_is_updated = False
        for o_auth_scope in o_auth_scopes_to_add:
            if o_auth_scope not in allowed_o_auth_scopes:
                allowed_o_auth_scopes.append(o_auth_scope)
                allowed_o_auth_scopes_is_updated = True

        if allowed_o_auth_scopes_is_updated:
            # Only update the allowed OAuth scopes of the client and keep all the other attributes unchanged.
            user_pool_client['AllowedOAuthScopes'] = allowed_o_auth_scopes
            idp_client.update_user_pool_client(
                **user_pool_client,
            )

        logging.info('add to user pool client scopes successfully')
        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.SUCCESS,
            data={},
            physical_resource_id=PHYSICAL_RESOURCE_ID
        ))
    except Exception as e:
        error_message = f'failed to add to user pool client scopes: {e}'
        logging.exception(error_message)

        client.send_cfn_response(CfnResponse(
            context=context,
            event=event,
            status=CfnResponseStatus.FAILED,
            data={},
            physical_resource_id=PHYSICAL_RESOURCE_ID,
            reason=error_message,
        ))
    finally:
        client.destroy()
