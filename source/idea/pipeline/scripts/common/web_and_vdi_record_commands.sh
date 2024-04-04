#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# Get Hosted Zone with provided Portal Domain Name
HOSTED_ZONES=$(aws route53 list-hosted-zones --query "HostedZones[?Name=='$PORTAL_DOMAIN.'].Id")
NUMBER_OF_HOSTED_ZONES=$(echo "$HOSTED_ZONES" | grep -o "hostedzone" | wc -l)

# Terminate if number of hosted zones matching Portal Domain Name is not 1
if [ "$NUMBER_OF_HOSTED_ZONES" -eq 0 ]; then
  echo "Unable to $WEB_AND_VDI_RECORD_ACTION records because there are no hosted zones with the domain: $PORTAL_DOMAIN"
  exit 1
fi
if [ "$NUMBER_OF_HOSTED_ZONES" -gt 1 ]; then
  echo "Unable to $WEB_AND_VDI_RECORD_ACTION records because of multiple hosted zones with the domain: $PORTAL_DOMAIN"
  exit 1
fi

HOSTED_ZONE_ID=$(echo "${HOSTED_ZONES[0]}" | cut -d / -f 3- | tr -d '[]\n"')
EXTERNAL_ALB_DNS=$(aws elbv2 describe-load-balancers --names "$CLUSTER_NAME-external-alb" --region "$AWS_REGION" --query "LoadBalancers[0].DNSName" | tr -d '"')
VDI_NLB_DNS=$(aws elbv2 describe-load-balancers --names "$CLUSTER_NAME-vdc-external-nlb" --region "$AWS_REGION" --query "LoadBalancers[0].DNSName" | tr -d '"')

# Create/Delete WEB and VDI Records
WEB_RECORD_ID=$(aws route53 change-resource-record-sets --hosted-zone-id "$HOSTED_ZONE_ID" --change-batch "{\"Changes\":[{\"Action\":\"$WEB_AND_VDI_RECORD_ACTION\",\"ResourceRecordSet\":{\"Name\":\"$WEB_PORTAL_DOMAIN\",\"Type\":\"CNAME\",\"TTL\":300,\"ResourceRecords\":[{\"Value\":\"$EXTERNAL_ALB_DNS\"}]}}]}" --query "ChangeInfo.Id" | tr -d '"')
VDI_RECORD_ID=$(aws route53 change-resource-record-sets --hosted-zone-id "$HOSTED_ZONE_ID" --change-batch "{\"Changes\":[{\"Action\":\"$WEB_AND_VDI_RECORD_ACTION\",\"ResourceRecordSet\":{\"Name\":\"$VDI_PORTAL_DOMAIN\",\"Type\":\"CNAME\",\"TTL\":300,\"ResourceRecords\":[{\"Value\":\"$VDI_NLB_DNS\"}]}}]}" --query "ChangeInfo.Id" | tr -d '"')
WEB_RECORD_STATUS=""
VDI_RECORD_STATUS=""
MAX_ATTEMPT=10
CURRENT_ATTEMPT=0
SLEEP_INTERVAL=30

# Wait until records have been created/deleted
while [ "$WEB_RECORD_STATUS" != "INSYNC" ] || [ "$VDI_RECORD_STATUS" != "INSYNC" ];
do
  ((CURRENT_ATTEMPT=CURRENT_ATTEMPT+1))
  if [[ ${CURRENT_ATTEMPT} -ge "$(($MAX_ATTEMPT-1))" ]]; then
      echo "error: Timed out waiting for records to $WEB_AND_VDI_RECORD_ACTION in hosted zone: ${PORTAL_DOMAIN}"
      return 1
  fi
  echo "Records ${WEB_AND_VDI_RECORD_ACTION} pending ... Waiting ${SLEEP_INTERVAL} s... Loop count is: ${CURRENT_ATTEMPT}/${MAX_ATTEMPT}"
  sleep ${SLEEP_INTERVAL}
  WEB_RECORD_STATUS=$(aws route53 get-change --id "$WEB_RECORD_ID" --query "ChangeInfo.Status" | tr -d '"')
  VDI_RECORD_STATUS=$(aws route53 get-change --id "$VDI_RECORD_ID" --query "ChangeInfo.Status" | tr -d '"')
  echo "Web Record Status: $WEB_RECORD_STATUS"
  echo "VDI Record Status: $VDI_RECORD_STATUS"
done

echo "Successfully ${WEB_AND_VDI_RECORD_ACTION} WEB and VDI records."

