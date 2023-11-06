#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

PUBLIC_IP=$(curl https://checkip.amazonaws.com/)

SG_EXTERNAL_ALB_INFO=$(aws ec2 describe-security-groups --region $AWS_REGION --filters Name=group-name,Values=$CLUSTER_NAME-external-load-balancer-security-group)
SG_BASTION_HOST_INFO=$(aws ec2 describe-security-groups --region $AWS_REGION --filters Name=group-name,Values=$CLUSTER_NAME-bastion-host-security-group)
SG_VDC_GATEWAY_INFO=$(aws ec2 describe-security-groups --region $AWS_REGION --filters Name=group-name,Values=$CLUSTER_NAME-vdc-gateway-security-group)

SG_EXTERNAL_ALB_ID=$(echo $SG_EXTERNAL_ALB_INFO | jq -r '.SecurityGroups[0].GroupId')
SG_BASTION_HOST_ID=$(echo $SG_BASTION_HOST_INFO | jq -r '.SecurityGroups[0].GroupId')
SG_VDC_GATEWAY_ID=$(echo $SG_VDC_GATEWAY_INFO | jq -r '.SecurityGroups[0].GroupId')

aws ec2 revoke-security-group-ingress --group-id $SG_EXTERNAL_ALB_ID --region $AWS_REGION --ip-permissions \
    IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges="[{CidrIp=$PUBLIC_IP/32}]" \
    IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges="[{CidrIp=$PUBLIC_IP/32}]"

aws ec2 revoke-security-group-ingress --group-id $SG_BASTION_HOST_ID --region $AWS_REGION --ip-permissions \
    IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges="[{CidrIp=$PUBLIC_IP/32}]"

aws ec2 revoke-security-group-ingress --group-id $SG_VDC_GATEWAY_ID --region $AWS_REGION --ip-permissions \
    IpProtocol=all,IpRanges="[{CidrIp=$PUBLIC_IP/32}]"
