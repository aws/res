# Research and Engineering Studio

# Documentation

https://docs.aws.amazon.com/res/latest/ug/overview.html

# Directories

## idea-administrator

Contains the files related to the initial install of the Research and Engineering Studio solution.

## idea-bootstrap

Contains the jinja templates needed throughout the solution.

## idea-cluster-manager

Contains everything needed for the cluster manager module (server set-up, api, etc).

## idea-data-model

Defines the data models used throughout the solution.

## idea-dcv-connection-gateway

## idea-sdk

Contains functions and base classes that are re-used throughout Research and Engineering Studio.

## idea-test-utils

Contains various utilities needed for tests.

## idea-virtual-desktop-controller

Contains everything needed for the vdc module (server set-up, api, etc).

## regional_pipeline_deployment.sh

Bash script to deploy BI+RES stack to regional accounts. It take path to json file containing Account configs and local .cdk.json file that it iterates over and deploys the stack. The script updates the PortalDomainName , CustomDomainNameforWebApp and CustomDomainNameforVDI values based on the region of the the account before deploying the stack. The [json file](https://code.amazon.com/packages/RESRegionalTestingConfig/blobs/b888adf06fce77066496a48b92cc12b2d1b4ad66/--/configuration/regional_account_config.json#L1) is stored in RESRegionalTestingConfig package. Make sure you have jq and ada installed locally. Run mwinit before running the script so the script is able to fetch credentials for each account and deploy the stack.

Steps to run the script:

* Install `jq` and `ada` if you don’t have already. `ada` can be installed by running `toolbox install ada`
* Run `mwinit --aea`
* Run the following command that will trigger the deployment. Pass the path to the config file and cdk json file to the script
```
./regional_pipeline_deployment.sh <path_to_json_config_file> <path_to_cdk_json_file>
```

