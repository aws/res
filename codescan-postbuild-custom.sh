#!/bin/bash
#--------------------------------------------------------------------
# Usage: this script must exit with a non-zero return code if the
# Viperlight scan fails.
#--------------------------------------------------------------------
. ./codescan-funcs.sh

echo ================================================================
echo ======     Viperlight Script `basename $0`
echo ================================================================
source_dir='./source'
solution_dir=`pwd`
VIPERLIGHT_SCAN_STRATEGY=${VIPERLIGHT_SCAN_STRATEGY:-"Enforce"}
VIPERLIGHT_PUBCHECK_STRATEGY=${VIPERLIGHT_PUBCHECK_STRATEGY:-"Monitor"}
PIPELINE_TYPE=${PIPELINE_TYPE:-"feature"}

# Create a temp folder for working data
viperlight_temp=/tmp/viperlight_scan # should work in most environments
if [ -d $viperlight_temp ]; then
    rm $viperlight_temp/*
    rmdir $viperlight_temp
fi
mkdir $viperlight_temp

export PATH=${PATH}:../viperlight/bin

failed_scans=0

scan_npm() {
    echo -----------------------------------------------------------
    echo NPM Scanning ${1}
    echo -----------------------------------------------------------
    folder_path=$(dirname ${1})
    viperlight scan -t ${folder_path} -m node-npmoutdated
    rc=$?
    if [ ${rc} -eq 0 ]; then
        echo SUCCESS
    elif [ ${rc} -eq 42 ]; then
        echo NOTHING TO SCAN
    else
        echo FAILED rc=${rc}
        if [ ${VIPERLIGHT_SCAN_STRATEGY} == "Enforce" ]; then
          ((failed_scans=failed_scans+1))
        fi
    fi
}

scan_py() {
    echo -----------------------------------------------------------
    echo Python Scanning $1
    echo -----------------------------------------------------------
    folder_path=`dirname $1`
    viperlight scan -t $folder_path -m notice-py
    rc=$?
    if [ $rc -eq 0 ]; then
        echo SUCCESS
    elif [ $rc -eq 42 ]; then
        echo NOTHING TO SCAN
    else
        echo FAILED rc=$rc
        if [ ${VIPERLIGHT_SCAN_STRATEGY} == "Enforce" ]; then
          ((failed_scans=failed_scans+1))
        fi
    fi
}

echo -----------------------------------------------------------
echo Scanning all Nodejs projects
echo -----------------------------------------------------------
find_all_node_projects ${viperlight_temp}
if [[ -e ${viperlight_temp}/scan_npm_list.txt ]]; then
    while read folder
        do
            scan_npm $folder
        done < $viperlight_temp/scan_npm_list.txt
else
    echo No node projects found
fi

echo -----------------------------------------------------------
echo Set up python virtual environment for pubcheck scan
echo -----------------------------------------------------------
tear_down_python_virtual_env ../
# Create a list of python folders in ${viperlight_temp}/scan_python_lists.txt
find_all_python_requirements ${viperlight_temp}
setup_python_virtual_env ../

# Install modules
if [[ -e ${viperlight_temp}/scan_python_list.txt ]]; then
    pip install bandit pip-licenses pip-audit -U
    while read folder
        do
            pip install -r $folder
        done < $viperlight_temp/scan_python_list.txt
else
    echo No python projects found
fi

echo -----------------------------------------------------------
echo Running publisher checks
echo -----------------------------------------------------------
viperlight pubcheck
rc=$?
if [ $rc -gt 0 ]; then
  if [ ${VIPERLIGHT_PUBCHECK_STRATEGY} == "Enforce" ]; then
    ((failed_scans=failed_scans+1))
  else
    echo Findings are present that are greater than threshold, but Strategy was set to Monitor
  fi
fi

if [ ${failed_scans} == 0 ]
then
    echo Scan completed successfully
else
    echo ${failed_scans} scans failed. Check previous messages for findings.
fi

exit ${failed_scans}