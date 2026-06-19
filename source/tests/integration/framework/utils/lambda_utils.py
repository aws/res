#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import time
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def set_backend_lambda_env_var(
    region: str, environment_name: str, key: str, value: Optional[str]
) -> None:
    """
    Set or remove an environment variable on the backend Lambda function.

    Args:
        region: AWS region where the Lambda function is deployed
        environment_name: RES environment name to construct the Lambda function name
        key: Environment variable key
        value: Environment variable value, or None to remove the key
    """
    lambda_client = boto3.client("lambda", region_name=region)
    function_name = f"{environment_name}-backend-lambda"

    try:
        logger.info(
            f"Getting current configuration for Lambda function: {function_name}"
        )
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        current_env_vars = response.get("Environment", {}).get("Variables", {})

        if value is not None:
            current_env_vars[key] = value
            logger.info(f"Setting {key}={value} for Lambda function: {function_name}")
        else:
            if key in current_env_vars:
                del current_env_vars[key]
                logger.info(f"Removing {key} from Lambda function: {function_name}")
            else:
                logger.info(
                    f"{key} not set on Lambda function: {function_name}, nothing to remove"
                )
                return

        lambda_client.update_function_configuration(
            FunctionName=function_name, Environment={"Variables": current_env_vars}
        )

        logger.info(
            f"Waiting for Lambda configuration update to take effect for {function_name}..."
        )
        _wait_for_lambda_config_update(lambda_client, function_name)

        logger.info(
            f"Successfully updated Lambda function {function_name} with {key}={value if value else 'removed'}"
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            logger.warning(
                f"Lambda function {function_name} not found. This may be expected if the backend Lambda is not deployed."
            )
        else:
            logger.error(f"Failed to update Lambda function {function_name}: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error updating Lambda function {function_name}: {e}")
        raise


def set_backend_lambda_test_mode(
    region: str, environment_name: str, enable: bool
) -> None:
    """
    Set RES_TEST_MODE environment variable on the backend Lambda function.

    Args:
        region: AWS region where the Lambda function is deployed
        environment_name: RES environment name to construct the Lambda function name
        enable: True to enable test mode, False to disable
    """
    set_backend_lambda_env_var(
        region, environment_name, "RES_TEST_MODE", "true" if enable else None
    )


def set_backend_lambda_dry_mode(
    region: str, environment_name: str, enable: bool
) -> None:
    """
    Set DRY_RUN_ENABLED environment variable on the backend Lambda function.

    Args:
        region: AWS region where the Lambda function is deployed
        environment_name: RES environment name to construct the Lambda function name
        enable: True to enable dry run mode, False to disable
    """
    set_backend_lambda_env_var(
        region, environment_name, "DRY_RUN_ENABLED", "true" if enable else None
    )


def _wait_for_lambda_config_update(
    lambda_client: Any,
    function_name: str,
    max_wait_time: int = 300,
    poll_interval: int = 5,
) -> None:
    """
    Wait for Lambda function configuration update to complete.

    Args:
        lambda_client: Boto3 Lambda client
        function_name: Name of the Lambda function
        max_wait_time: Maximum time to wait in seconds (default: 5 minutes)
        poll_interval: Time between polls in seconds (default: 5 seconds)
    """
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        try:
            response = lambda_client.get_function_configuration(
                FunctionName=function_name
            )
            current_status = response.get("LastUpdateStatus", "Unknown")

            logger.debug(f"Lambda {function_name} status: {current_status}")

            if current_status == "Successful":
                logger.info(
                    f"Lambda configuration update completed successfully for {function_name}"
                )
                return
            elif current_status == "Failed":
                raise Exception(
                    f"Lambda configuration update failed for {function_name}"
                )
            elif current_status in ["InProgress"]:
                # Continue waiting
                logger.debug(
                    f"Lambda configuration update still in progress for {function_name}"
                )
            else:
                logger.warning(
                    f"Unknown Lambda status '{current_status}' for {function_name}"
                )

            time.sleep(poll_interval)

        except ClientError as e:
            logger.error(
                f"Error checking Lambda configuration status for {function_name}: {e}"
            )
            raise

    raise TimeoutError(
        f"Timeout waiting for Lambda configuration update to complete for {function_name} "
        f"after {max_wait_time} seconds"
    )
