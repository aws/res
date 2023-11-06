# RES build pipeline

This project utilizes cdk pipelines for setting up a development pipeline that builds, deploys, and tests RES.

## Prerequisites

1. Create a virtual environment and activate it, using the version of Python as specified in the `requires-python`
   field in `pyproject.toml`
2. Install the dependencies in your virtual environment

        pip install -r requirements/dev.txt
        pip install -e source/idea/idea-data-model/src
        pip install -e ".[dev]"

3. Create a CodeCommit repo and add it as a remote

        git remote add codecommit <codecommit repo url>

## Deploy pipeline

1. Deploy the pipeline stack, using the context to set the repo name and branch, optional context for publishing cdk synth templates to a S3 bucket can be set to true

        npx cdk deploy RESBuildPipelineStack -c repository_name=<repo name> -c branch_name=<branch name> -c publish_templates=<true or false> -c ecr_public_repository_name=<ecr public repository name>

## Developer workflow

Use the CodeCommit repo as a place to develop code. Pushing to it will trigger the pipeline and run all the automated
tests. When you are satisfied with the commits, you can push upstream to origin or submit the commits for review.
