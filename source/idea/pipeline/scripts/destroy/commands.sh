#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

resStacks=("Deploy-$INSTALL_STACK_NAME"
            "$CLUSTER_NAME-bootstrap"
            "$CLUSTER_NAME-cluster"
            "$CLUSTER_NAME-metrics"
            "$CLUSTER_NAME-directoryservice"
            "$CLUSTER_NAME-identity-provider"
            "$CLUSTER_NAME-analytics"
            "$CLUSTER_NAME-shared-storage"
            "$CLUSTER_NAME-cluster-manager"
            "$CLUSTER_NAME-vdc"
            "$CLUSTER_NAME-bastion-host"
);

#Collection of all RES CFN Stack IDs
resStackIds=();
for stack in ${resStacks[@]}; do
    stackId=$(aws cloudformation describe-stacks --stack-name $stack --region $AWS_REGION | jq -r '.Stacks[0].StackId');
    resStackIds+=( $stackId );
done

declare -A removedStackIds;
for stackId in ${resStackIds[@]}; do
    removedStackIds+=( [$stackId]=0 );
done

#Triggers deletion of Deploy-$INSTALL_STACK_NAME
aws cloudformation delete-stack --stack-name Deploy-$INSTALL_STACK_NAME --region $AWS_REGION;

#Review Deletion of RES CFN Stacks Loop
waitMinutes=0;
failedStackId="";
removedStackCount=0
while [[ ${#resStackIds[@]} -ne $removedStackCount && $failedStackId == "" ]]
do
    echo "$waitMinutes minutes have past...";
    echo "Showing status of remaining RES CFN stacks pending deletion:";
    for stackId in ${resStackIds[@]}; do
        if [[ ${removedStackIds[$stackId]} -eq 0 ]] ; then
            stackStatus=$(aws cloudformation describe-stacks --stack-name $stackId --region $AWS_REGION | jq -r '.Stacks[0].StackStatus');
            echo "$stackId: $stackStatus";
            if [[ $stackStatus == "DELETE_COMPLETE" ]] ; then
                removedStackIds[$stackId]=1;
                let removedStackCount++;
            elif [[ $stackStatus == "DELETE_FAILED" ]] ; then
                failedStackId=$stackId;
                break;
            fi
        fi
    done
    echo;
    sleep 60;
    let waitMinutes++;
done

#Verification of RES deletion
if [[ $failedStackId != "" ]] ; then
    echo "RES deployment deletion FAILED";
    echo "$failedStackId: DELETE_FAILED";
    exit 1;
else
    echo "All RES CFN stacks have been deleted";
fi
