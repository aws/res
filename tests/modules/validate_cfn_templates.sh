#!/bin/bash

GEM=$(which gem)

if [[ -z "$GEM" ]]
then
  echo "Missing required libraries: Gem & Ruby do not seems to be installed on the system"
  exit 1
fi

echo "Installing the latest version of cfn-nag (sudo required)"
sudo $GEM install cfn-nag

CFN_NAG_SCAN=$(which cfn_nag_scan)
CWD=$1
$CFN_NAG_SCAN  -i $CWD/../deployment/scale-out-computing-on-aws.template --fail-on-warnings
for template in $(ls $CWD/../deployment/templates);
    do
       $CFN_NAG_SCAN  -i $CWD/../deployment/templates/$template --fail-on-warnings || ec2=$?
done