#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

function process_authorize_security_group_ingress_response {
  local exit_code=$?

  if [ $exit_code -ne 0 ]; then
    if [[ "$response" == *"An error occurred (InvalidPermission.Duplicate)"* ]]; then
      echo "Skip existing security group rule"
    else
      echo "Failed to add security group rule: $response"
      exit $exit_code
    fi
  else
    echo "$response"
  fi

  return 0
}

PUBLIC_IP=$(curl https://checkip.amazonaws.com/)

if [[ -z $CLUSTERADMIN_USERNAME || -z $CLUSTERADMIN_PASSWORD ]]; then
  echo 'skip clusteradmin credentials setup'
else
  USERPOOLID=`aws cognito-idp list-user-pools --region $AWS_REGION --max-results 60 --query 'UserPools[?Name==\`'$CLUSTER_NAME-user-pool'\`].Id' --output text`

  aws cognito-idp admin-set-user-password --user-pool-id "$USERPOOLID" --region "$AWS_REGION" --username "$CLUSTERADMIN_USERNAME" --password "$CLUSTERADMIN_PASSWORD" --permanent
fi

SG_EXTERNAL_ALB_INFO=$(aws ec2 describe-security-groups --region $AWS_REGION --filters Name=group-name,Values=$CLUSTER_NAME-external-load-balancer-security-group)
SG_BASTION_HOST_INFO=$(aws ec2 describe-security-groups --region $AWS_REGION --filters Name=group-name,Values=$CLUSTER_NAME-bastion-host-security-group)
SG_VDC_GATEWAY_INFO=$(aws ec2 describe-security-groups --region $AWS_REGION --filters Name=group-name,Values=$CLUSTER_NAME-vdc-gateway-security-group)

SG_EXTERNAL_ALB_ID=$(echo $SG_EXTERNAL_ALB_INFO | jq -r '.SecurityGroups[0].GroupId')
SG_BASTION_HOST_ID=$(echo $SG_BASTION_HOST_INFO | jq -r '.SecurityGroups[0].GroupId')
SG_VDC_GATEWAY_ID=$(echo $SG_VDC_GATEWAY_INFO | jq -r '.SecurityGroups[0].GroupId')

response=$(aws ec2 authorize-security-group-ingress --group-id $SG_EXTERNAL_ALB_ID --region $AWS_REGION --ip-permissions \
    IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges="[{CidrIp=$PUBLIC_IP/32,Description='HTTP access to integration tests environment'}]" \
    IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges="[{CidrIp=$PUBLIC_IP/32,Description='HTTPS access to integration tests environment'}]" 2>&1)
process_authorize_security_group_ingress_response

response=$(aws ec2 authorize-security-group-ingress --group-id $SG_BASTION_HOST_ID --region $AWS_REGION --ip-permissions \
    IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges="[{CidrIp=$PUBLIC_IP/32,Description='SSH access to integration tests environment'}]" 2>&1)
process_authorize_security_group_ingress_response

response=$(aws ec2 authorize-security-group-ingress --group-id $SG_VDC_GATEWAY_ID --region $AWS_REGION --ip-permissions \
    IpProtocol=all,IpRanges="[{CidrIp=$PUBLIC_IP/32,Description='Allow all traffic to integration tests environment'}]" 2>&1)
process_authorize_security_group_ingress_response
