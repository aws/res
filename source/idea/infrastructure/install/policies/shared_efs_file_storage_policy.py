#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from aws_cdk import aws_iam as iam


class SharedEfsFileStoragePolicy:
    """
    EFS File System Policy to prevent anonymous access and enforce TLS
    """

    @staticmethod
    def create_policy() -> iam.PolicyDocument:
        return iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    sid="efs-statement",
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "elasticfilesystem:ClientRootAccess",
                        "elasticfilesystem:ClientWrite",
                        "elasticfilesystem:ClientMount",
                    ],
                    principals=[iam.AnyPrincipal()],
                    conditions={
                        "Bool": {"elasticfilesystem:AccessedViaMountTarget": "true"}
                    },
                ),
                iam.PolicyStatement(
                    sid="efs-enforce-tls",
                    effect=iam.Effect.DENY,
                    actions=["*"],
                    principals=[iam.AnyPrincipal()],
                    conditions={"Bool": {"aws:SecureTransport": "false"}},
                ),
            ]
        )
