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
    'CognitoConstructParams',
    'get_cognito_construct_params'
)

import os
from typing import Literal
from ideadatamodel import SocaBaseModel

class CognitoConstructParams(SocaBaseModel):
    advanced_security_mode: Literal['AUDIT', 'ENFORCED', 'OFF']
    auto_verified_attributes: list[Literal['email', 'phone']]
    user_invitation_email_body: str
    user_invitation_email_subject: str

def get_cognito_user_invitation_email_subject(cluster_name: str):
    return f'Invitation to Join RES Environment: {cluster_name}'


def get_user_invitation_email_body(cluster_name: str, external_alb_dns: str):
    external_endpoint = f'https://{external_alb_dns}'

    email_message = [
        '<p>Hello <b>{username},</b></p>',
        f'<p>You have been invited to join the <b>{cluster_name}</b> environment.</p>',
        f'<p>Your temporary password is:</p>',
        '<h3>{####}</h3>',
        '<p>You can sign in to your account using the link below: <br/>',
        f'<a href="{external_endpoint}">{external_endpoint}</a></p>',
        f'<p>---<br/>',
        f'<b>RES Environment Admin</b></p>'
    ]
    return os.linesep.join(email_message)

def get_cognito_construct_params(cluster_name: str, external_alb_dns: str) -> CognitoConstructParams:
    return CognitoConstructParams(advanced_security_mode='AUDIT', auto_verified_attributes=['email'], user_invitation_email_body=get_user_invitation_email_body(cluster_name, external_alb_dns), user_invitation_email_subject=get_cognito_user_invitation_email_subject(cluster_name))
