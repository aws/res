# RES host modules pipeline

This project utilizes cdk pipelines for setting up a development pipeline that builds, tests, and publishes RES host modules.

## Prerequisites

1. Install the dependencies in your virtual environment

        pip install -r requirements/dev.txt

2. Create a CodeCommit repo and add it as a remote

        git remote add codecommit <codecommit repo url>

## Deploy pipeline

1. Deploy the pipeline stack, using the context to set the repo name and branch, optional context for publishing cdk synth templates to a S3 bucket can be set to true

        npx cdk deploy RESHostModulesPipelineStack -c repository_name=<repo name> -c branch_name=<branch name> -c publish_modules=<true | false> -c public_release= <true | false> -c s3_bucket_name=<bucket_name>

### Configuration

#### Context Variables

The pipeline uses context variables to configure its behavior. These can be specified in the `cdk.json` file or passed as CLI arguments during deployment.

Here are the available context variables:

- **`repository_name`**: (Required) The name of the CodeCommit repository containing the source code. Defaults to `DigitalEngineeringPlatform`.
- **`branch_name`**: (Required) The branch in the CodeCommit repository to monitor for changes. Defaults to `develop`.
- **`publish_modules`**: (Required) A flag indicating whether to publish modules. Set to `"true"` or `"false"`.
- **`public_release`**: (Optional) A flag indicating whether the release is public. If `"true"`, modules will be published to regional public RES S3 buckets.
- **`s3_bucket_name`**: (Optional) The S3 bucket name to use when `public_release` is `"false"`. Required if `public_release` is `"false"`.

## Developer Workflow

To deploy the pipeline in a local development AWS account:

1. **Set `public_release` to `false`:** This ensures that the modules are not published to regional S3 buckets but instead to a specified local S3 bucket.

2. **Provide your own S3 bucket:** Use the `s3_bucket_name` context variable to specify the local S3 bucket where the modules will be published.

Once deployed, the modules will be published to your specified S3 bucket, making them available for testing and development purposes.
