## Proxy Lambda

### Deploy Proxy Lambda in an Independent Stack
Deploying Proxy Lambda in an independent stack enables quick testing in infrastructure changes.
This deployment creates a Proxy Lambda on top of existing RES resources and create a rule in RES external ALB
to direct calls for `/awsproxy/*` to the proxy Lambda.

To deploy the Proxy Lambda independently in a separate stack,
add the following code block in file [app.py](../../app.py) and replace the input values with
resource ids from your RES deployment.

```python
    ProxyStack(
        app,
        "ProxyStack",
        {
            "target_group_priority": 99,
            "ddb_users_table_name": "<YOUR_CLUSTER_NAME>.accounts.users",
            "ddb_groups_table_name": "<YOUR_CLUSTER_NAME>.accounts.groups",
            "ddb_cluster_settings_table_name": "<YOUR_CLUSTER_NAME>.cluster-settings",
            "cluster_name": "local", # Use a different cluster name here than your deployed env to avoid conflict
        },
        vpc_id="<YOUR_VPC_ID>",
        lambda_layer_arn="<YOUR_LAMBDA_LAYER_ARN>",
        synthesizer=install_synthesizer,
    )
```

Since we're passing Lambda layer to install and package Python dependencies for this Lambda function, deploying
through the pipeline would be needed to get the lambda layer created.

Make sure you have CDK cli installed globally through NPM, as the Python CDK depends on it.
In you Python .venv, install dependencies in `requirements/dev.txt`, then run the following command to deploy

```
cdk deploy ProxyStack
```

### Use the Proxy API
The Proxy API is an admin only API designed to support UI enhancement. The signature of the request depends on the
signature of the AWS Service API you're trying to call. Right now, the Proxy API has the following 3 use cases:
* AWS Budget: [DescribeBudgets](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_DescribeBudgets.html)
* Amazon Elastic File System: [DescribeFileSystems](https://docs.aws.amazon.com/efs/latest/ug/API_DescribeFileSystems.html)
* Amazon FSx: [DescribeFileSystems](https://docs.aws.amazon.com/fsx/latest/APIReference/API_DescribeFileSystems.html)

Check out the integration tests in folder [aws_proxy_integration](../../../tests/aws_proxy_integration) for the request signature
for the above 3 endpoints.

To use the Proxy API for methods aside from the above three mentioned, you can find the request signature through:
1. Check the AWS official API documentation for the method
2. Check how AWS Console is calling the method
3. Ask Amazon Q

Once you find the API signature, please add new integration tests and update this document with the new method.
