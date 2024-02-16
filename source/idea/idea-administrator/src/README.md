# Digital Engineering Portal on AWS

# Documentation

https://docs.aws.amazon.com/res/latest/ug/overview.html

# Directories

The idea-adminsitrator folder contains various files related to the initial install of IDEA via CDK (cluster install and management).

## ideaadministrator

Contains the CDK.

### app

Contains the CDK files as well as various helper files.

#### cdk

Contains the files related to the cdk. This includes the stacks and constructs. As well as files that contains classes for invoking the cdk.

##### constructs

contains various constructs that are used in the stacks.

##### stacks

Contains the main stacks that are deployed in the account. There is a stack for each CloudFormation template deployed as well as a base stack that servers as a parent stack for all other stacks. The stacks are made up of various constructs most of which are defined in the constructs folder.

##### cdk_app.py

Contains the class the defines each stack.

##### cdk_invoker.py

Contains the class that is used to invoke the cdk.

##### idea_code_asset.py

Contains the class that is used to build the lambda code assets.

### integration_tests

Contains a single integration test for the scheduler.

## ideaadministrator_meta

Files containing the metadata (name and version) for the idea administrator.
