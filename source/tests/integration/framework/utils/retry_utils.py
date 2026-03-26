#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

"""
Retry utilities for integration tests.

This module provides retry functionality for API calls that may fail
temporarily due to services not being ready after deployment.
"""

import logging
import time
from typing import Any, Callable, Optional, Tuple, Type

logger = logging.getLogger(__name__)


def retry_with_backoff(
    func: Callable[[], Any],
    max_retries: int,
    initial_delay: int,
    backoff_factor: int,
    max_delay: int,
    exceptions: Tuple[Type[BaseException], ...],
    success_condition: Optional[Callable[[Any], bool]] = None,
) -> Any:
    """
    Retry a function with exponential backoff.
    """
    last_exception: Optional[BaseException] = None
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Attempt {attempt + 1}/{max_retries + 1} for {func.__name__}")
            result = func()

            # Check success condition if provided
            if success_condition and not success_condition(result):
                raise ValueError("Success condition not met")

            logger.debug(
                f"Successfully executed {func.__name__} on attempt {attempt + 1}"
            )
            return result

        except exceptions as e:
            last_exception = e
            logger.warning(
                f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}"
            )

            # Don't sleep after the last attempt
            if attempt < max_retries:
                logger.info(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)
            else:
                logger.error(
                    f"All {max_retries + 1} attempts failed for {func.__name__}"
                )

    # Re-raise the last exception if all retries failed
    if last_exception is not None:
        raise last_exception
    else:
        raise RuntimeError("All retry attempts failed but no exception was captured")


def retry_api_call(
    func: Callable[[], Any],
    max_retries: int,
    initial_delay: int,
    server_error_codes: Tuple[str, ...] = ("500", "502", "503", "504"),
) -> Any:
    """
    Retry an API call specifically for server errors that may occur
    when services are not ready after deployment.
    """

    def should_retry(exception: Exception) -> bool:
        """Check if the exception indicates a server error worth retrying."""
        error_str = str(exception)
        return any(code in error_str for code in server_error_codes)

    def retry_func() -> Any:
        try:
            return func()
        except Exception as e:
            if should_retry(e):
                raise e  # Will be caught by retry logic
            else:
                # Don't retry for client errors (4xx) or other non-server errors
                logger.info(f"Not retrying for non-server error: {str(e)}")
                raise e

    return retry_with_backoff(
        retry_func,
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=2,
        max_delay=120,
        exceptions=(Exception,),
    )
