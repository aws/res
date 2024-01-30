#!/usr/bin/env bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

resStacks=("Deploy-$INSTALL_STACK_NAME"
            "$CLUSTER_NAME-bootstrap"
            "$CLUSTER_NAME-cluster"
            "$CLUSTER_NAME-metrics"
            "$CLUSTER_NAME-directoryservice"
            "$CLUSTER_NAME-identity-provider"
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
removedStackCount=0;
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

#Verification of RES CloudFormation stacks deletion
if [[ $failedStackId != "" ]] ; then
    echo "RES deployment deletion FAILED";
    echo "$failedStackId: DELETE_FAILED";
    exit 1;
else
    echo "All RES CFN stacks have been deleted";
    echo;
fi

echo "Cleaning up all RES EFS file systems in VPC using $CLUSTER_NAME-shared-storage-security-group...";

#Pulling VPC ID from provided SSM parameter to VPC ID of BI
if [[ $BATTERIES_INCLUDED == "true" ]]; then
    VPC_ID_INFO=$(aws ssm get-parameter --name $VPC_ID)
    VPC_ID=$(echo $VPC_ID_INFO | jq -r '.Parameter.Value')
fi

#Collect all pertinent EFS file systems
EFS_FILE_SYSTEMS=$(aws efs describe-file-systems --region $AWS_REGION --no-paginate --query "FileSystems[?Tags[?Key == 'res:EnvironmentName' && Value == '$CLUSTER_NAME']][].FileSystemId");

if [[ $EFS_FILE_SYSTEMS != "[]" ]] ; then
    #Loop to delete all EFS file systems
    echo $EFS_FILE_SYSTEMS | jq -r '.[]' | while read FileSystemId; do
        FILE_SYSTEM_MOUNT_TARGETS=$(aws efs describe-mount-targets --region $AWS_REGION --no-paginate --file-system-id $FileSystemId);
        EFS_VPC_ID=$(echo $FILE_SYSTEM_MOUNT_TARGETS | jq -r '.MountTargets[0].VpcId');
        if [[ $EFS_VPC_ID == $VPC_ID ]] ; then
            #Deleting all MountTargets of EFS file system
            echo $FILE_SYSTEM_MOUNT_TARGETS | jq -r '.MountTargets[].MountTargetId' | while read MountTargetId; do
                echo "Deleting MountTarget $MountTargetId of $FileSystemId...";
                aws efs delete-mount-target --region $AWS_REGION --mount-target-id $MountTargetId;
            done
            sleep 90;
            #Deleting EFS file system
            echo "Deleting EFS file system $FileSystemId...";
            echo;
            aws efs delete-file-system --region $AWS_REGION --file-system-id $FileSystemId;
        else
            echo "EFS file system not in RES VPC, skipping...";
        fi
    done
    echo "Waiting 5 minutes for EFS file systems in VPC to finish deleting...";
    sleep 300;
else
    echo "No RES EFS file systems for $CLUSTER_NAME detected in VPC to delete!";
fi
echo;

echo "Cleaning up all FSx OnTAP file systems in VPC using $CLUSTER_NAME-shared-storage-security-group...";

#Collect all pertinent FSx ONTAP file systems
FSX_ONTAP_FILE_SYSTEMS=$(aws fsx describe-file-systems --region $AWS_REGION --no-paginate --query "FileSystems[?Tags[?Key == 'res:EnvironmentName' && Value == '$CLUSTER_NAME'] && VpcId == '$VPC_ID'][].FileSystemId");

if [[ $FSX_ONTAP_FILE_SYSTEMS != "[]" ]] ; then
    #Loop to delete all FSx ONTAP file systems
    echo $FSX_ONTAP_FILE_SYSTEMS | jq -r '.[]' | while read FileSystemId; do
        #Deleting all non-root volumes of FSx ONTAP file system
        echo "Deleting all non-root volumes of $FileSystemId...";
        FSX_VOLUMES=$(aws fsx describe-volumes --region $AWS_REGION --no-paginate --filters Name=file-system-id,Values=$FileSystemId --query "Volumes[?!(OntapConfiguration.StorageVirtualMachineRoot)][].VolumeId");
        echo $FSX_VOLUMES | jq -r '.[]' | while read VolumeId; do
            echo "Deleting Volume $VolumeId of $FileSystemId...";
            aws fsx delete-volume --region $AWS_REGION --volume-id $VolumeId --ontap-configuration SkipFinalBackup=true;
        done
        sleep 90;
        #Deleting all SVMs of FSx ONTAP file system
        echo;
        echo "Deleting all storage virtual machines of $FileSystemId...";
        FSX_SVMS=$(aws fsx describe-storage-virtual-machines --region $AWS_REGION --no-paginate --filters Name=file-system-id,Values=$FileSystemId --query "StorageVirtualMachines[].StorageVirtualMachineId");
        echo $FSX_SVMS | jq -r '.[]' | while read StorageVirtualMachineId; do
            echo "Deleting SVM $StorageVirtualMachineId of $FileSystemId...";
            aws fsx delete-storage-virtual-machine --region $AWS_REGION --storage-virtual-machine-id $StorageVirtualMachineId;
        done
        sleep 120;
        #Deleting FSx ONTAP file system
        echo;
        echo "Deleting FSx ONTAP file system $FileSystemId...";
        aws fsx delete-file-system --region $AWS_REGION --file-system-id $FileSystemId;
        echo;
    done
    echo "Waiting 15 minutes for FSx ONTAP file systems in VPC to finish deleting...";
    sleep 900
else
    echo "No RES FSx ONTAP file systems for $CLUSTER_NAME detected in VPC to delete!";
fi
echo;

echo "All RES shared-storage file systems in VPC have been deleted!";
echo;
echo "Deleting $CLUSTER_NAME-shared-storage-security-group...";

SG_SHARED_STORAGE_INFO=$(aws ec2 describe-security-groups --region $AWS_REGION --filters Name=group-name,Values=$CLUSTER_NAME-shared-storage-security-group Name=vpc-id,Values=$VPC_ID);

SG_SHARED_STORAGE_ID=$(echo $SG_SHARED_STORAGE_INFO | jq -r '.SecurityGroups[0].GroupId');

aws ec2 delete-security-group --group-id $SG_SHARED_STORAGE_ID;

echo "$CLUSTER_NAME-shared-storage-security-group has been deleted!";