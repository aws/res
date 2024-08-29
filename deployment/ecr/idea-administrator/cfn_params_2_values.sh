#!/bin/bash

aws_partition=${1}
aws_region=${2}
aws_account_id=${3}
aws_dns_suffix=${4}
cluster_name=${5}
administrator_email=${6}
ssh_key_pair_name=${7}
client_ip1=${8}
client_ip2=${9}
vpc_id=${10}
pub_subnets=${11}
pvt_subnets=${12}
storage_home_provider=${13}
home_fs_id=${14}

values_file="/root/.idea/clusters/${5}/${2}/values.yml"

prt_subnets(){
    for sn in $(echo $1| tr ',' ' ')
    do
        echo "- ${sn}"
    done
}

dir_name=$(dirname ${values_file})

mkdir -p ${dir_name}

rm -f ${values_file}
cat << EOF1 > ${values_file}
_regenerate: false
aws_partition: ${aws_partition}
aws_region: ${aws_region}
aws_account_id: ${aws_account_id}
aws_dns_suffix: ${aws_dns_suffix}
cluster_name: ${cluster_name}
administrator_email: ${administrator_email}
ssh_key_pair_name: ${ssh_key_pair_name}
client_ip:
- ${client_ip1}
- ${client_ip2}
alb_public: true
use_vpc_endpoints: true
directory_service_provider: aws_managed_activedirectory
enable_aws_backup: true
kms_key_type: aws-managed
use_existing_vpc: true
vpc_id: ${vpc_id}
existing_resources:
- subnets:public
- subnets:private
- shared-storage:home
public_subnet_ids:
EOF1
prt_subnets ${pub_subnets} >> ${values_file}
cat << EOF2 >> ${values_file}
private_subnet_ids:
EOF2
prt_subnets ${pvt_subnets} >> ${values_file}
cat << EOF3 >> ${values_file}
storage_home_provider: ${storage_home_provider}
use_existing_home_fs: true
existing_home_fs_id: ${home_fs_id}
enabled_modules:
- virtual-desktop-controller
- bastion-host
metrics_provider: cloudwatch
base_os: amazonlinux2
instance_type: m5.large
volume_size: '200'
EOF3
