#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import os
from typing import Union

import aws_cdk
import aws_cdk as cdk
import constructs
from aws_cdk import CfnCondition, Fn
from aws_cdk import aws_cognito as cognito
from res.constants import (  # type: ignore
    COGNITO_MAX_ID_INCLUSIVE,
    COGNITO_MIN_ID_INCLUSIVE,
    COGNITO_UID_ATTRIBUTE,
)

from idea.batteries_included.parameters.parameters import BIParameters
from idea.infrastructure.install import constants
from idea.infrastructure.install.constructs.base import ResBaseConstruct
from idea.infrastructure.install.parameters.common import CommonKey
from idea.infrastructure.install.parameters.parameters import RESParameters


class UserPool(ResBaseConstruct):

    def __init__(
        self,
        scope: constructs.Construct,
        name: str,
        parameters: Union[RESParameters, BIParameters],
        domain_uuid: str,
        props: cognito.UserPoolProps = cognito.UserPoolProps(),
    ):
        self.scope = scope
        self.props = props
        self.domain_uuid = domain_uuid
        self.cluster_name = parameters.get_str(CommonKey.CLUSTER_NAME)

        super().__init__(scope, name, cluster_name=self.cluster_name)

        self.build_user_pool()

    def build_user_pool(self) -> None:
        account_recovery = self.props.account_recovery
        if account_recovery is None:
            account_recovery = cognito.AccountRecovery.EMAIL_ONLY
        auto_verify = self.props.auto_verify
        if auto_verify is None:
            auto_verify = cognito.AutoVerifiedAttrs(email=True, phone=False)
        custom_attributes = self.props.custom_attributes
        if custom_attributes is None:
            custom_attributes = {
                "cluster_name": cognito.StringAttribute(mutable=True),
                "aws_region": cognito.StringAttribute(mutable=True),
                "password_last_set": cognito.NumberAttribute(mutable=True),
                "password_max_age": cognito.NumberAttribute(mutable=True),
                f"{COGNITO_UID_ATTRIBUTE}": cognito.NumberAttribute(
                    min=COGNITO_MIN_ID_INCLUSIVE, max=COGNITO_MAX_ID_INCLUSIVE
                ),
            }
        mfa = self.props.mfa
        if mfa is None:
            mfa = cognito.Mfa.OPTIONAL
        mfa_second_factor = self.props.mfa_second_factor
        if mfa_second_factor is None:
            mfa_second_factor = cognito.MfaSecondFactor(otp=True, sms=False)

        removal_policy = self.props.removal_policy
        if removal_policy is None:
            removal_policy = cdk.RemovalPolicy.DESTROY

        self_sign_up_enabled = self.props.self_sign_up_enabled
        if self_sign_up_enabled is None:
            self_sign_up_enabled = False

        sign_in_aliases = self.props.sign_in_aliases
        if sign_in_aliases is None:
            sign_in_aliases = cognito.SignInAliases(
                username=True, preferred_username=False, phone=False, email=True
            )

        sign_in_case_sensitive = self.props.sign_in_case_sensitive
        if sign_in_case_sensitive is None:
            sign_in_case_sensitive = False

        standard_attributes = self.props.standard_attributes
        if standard_attributes is None:
            standard_attributes = cognito.StandardAttributes(
                email=cognito.StandardAttribute(mutable=True, required=True)
            )
        user_invitation = self.props.user_invitation
        if user_invitation is None:
            user_invitation = cognito.UserInvitationConfig(
                email_subject=f"({self.cluster_name}) Your IDEA Account",
                email_body=f"""
                Hello <b>{{username}}</b>,
                <br/><br/>
                You have been invited to join the {self.cluster_name} cluster.
                <br/>
                Your temporary password is <b>{{####}}</b>
                """,
            )

        user_pool_name = self.props.user_pool_name
        if user_pool_name is None:
            user_pool_name = f"{self.cluster_name}-user-pool"

        no_security_mode_condition = CfnCondition(
            self.scope,
            "no-advanced-security-mode-condition",
            expression=Fn.condition_or(
                *[
                    Fn.condition_equals(aws_cdk.Aws.REGION, region)
                    for region in constants.CAVEATS.get(
                        "COGNITO_ADVANCED_SECURITY_UNAVAIL_REGION_LIST", []
                    )
                ]
            ),
        )

        advanced_security_mode = Fn.condition_if(
            no_security_mode_condition.logical_id,
            cognito.AdvancedSecurityMode.OFF,
            cognito.AdvancedSecurityMode.AUDIT,
        ).to_string()

        feature_plan = Fn.condition_if(
            no_security_mode_condition.logical_id,
            cognito.FeaturePlan.ESSENTIALS,
            cognito.FeaturePlan.PLUS,
        ).to_string()

        self.user_pool = cognito.UserPool(
            self,
            self.name,
            account_recovery=account_recovery,
            auto_verify=auto_verify,
            custom_attributes=custom_attributes,
            deletion_protection=True,
            mfa=mfa,
            mfa_second_factor=mfa_second_factor,
            removal_policy=removal_policy,
            self_sign_up_enabled=self_sign_up_enabled,
            sign_in_aliases=sign_in_aliases,
            sign_in_case_sensitive=sign_in_case_sensitive,
            standard_attributes=standard_attributes,
            user_invitation=user_invitation,
            user_pool_name=user_pool_name,
        )

        raw_cognito_userpool: cognito.CfnUserPool = self.user_pool.node.default_child  # type: ignore
        raw_cognito_userpool.add_property_override(
            "UserPoolAddOns.AdvancedSecurityMode", advanced_security_mode
        )
        raw_cognito_userpool.add_property_override("UserPoolTier", feature_plan)
        self.add_common_tags(self.user_pool)

        self.domain = self.user_pool.add_domain(
            id="domain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"{self.cluster_name}-{self.domain_uuid}"
            ),
        )

    @staticmethod
    def get_cognito_user_invitation_email_subject(cluster_name: str) -> str:
        return f"Invitation to Join RES Environment: {cluster_name}"

    @staticmethod
    def get_user_invitation_email_body(cluster_name: str, external_alb_dns: str) -> str:
        external_endpoint = f"https://{external_alb_dns}"

        email_message = [
            "<p>Hello <b>{username},</b></p>",
            f"<p>You have been invited to join the <b>{cluster_name}</b> environment.</p>",
            f"<p>Your temporary password is:</p>",
            "<h3>{####}</h3>",
            "<p>You can sign in to your account using the link below: <br/>",
            f'<a href="{external_endpoint}">{external_endpoint}</a></p>',
            f"<p>---<br/>",
            f"<b>RES Environment Admin</b></p>",
        ]
        return os.linesep.join(email_message)

    def get_domain_url(self) -> str:
        fips_condition = CfnCondition(
            self.scope,
            "fips-condition",
            expression=Fn.condition_or(
                *[
                    Fn.condition_equals(aws_cdk.Aws.REGION, region)
                    for region in constants.CAVEATS.get(
                        "COGNITO_REQUIRE_FIPS_ENDPOINT_REGION_LIST", []
                    )
                ]
            ),
        )
        return Fn.condition_if(
            fips_condition.logical_id,
            self.domain.base_url(fips=True),
            self.domain.base_url(fips=False),
        ).to_string()
