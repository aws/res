#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from pytest import fixture

from ideaadministrator.integration_tests.test_context import TestContext
from ideaadministrator.integration_tests.test_invoker import TestInvoker
from ideasdk.utils import Utils

# from ideaadministrator.app_main import run_integration_tests


@fixture(scope="session")
def module(request):
    return request.config.getoption("--module")


@fixture(scope="session")
def cluster_name(request):
    return request.config.getoption("--cluster-name")


@fixture(scope="session")
def aws_region(request):
    return request.config.getoption("--aws-region")


@fixture(scope="session")
def admin_username(request):
    return request.config.getoption("--admin-username")


@fixture(scope="session")
def admin_password(request):
    return request.config.getoption("--admin-password")


def test_integ_tests(module, cluster_name, aws_region, admin_username, admin_password):
    print(f"Starting integ tests for {module}")
    run_integration_tests(
        cluster_name=cluster_name,
        aws_region=aws_region,
        admin_username=admin_username,
        admin_password=admin_password,
        param={},
        module_set="",
        modules=[module],
    )
    print(f"Successfully ran integ tests for {module}")


def run_integration_tests(
    cluster_name: str,
    aws_region: str,
    admin_username: str,
    admin_password: str,
    param: tuple,
    module_set: str,
    modules,
):
    # dedupe and convert to list
    module_ids_to_test = []
    for module_id in modules:
        if module_id in module_ids_to_test:
            continue
        module_ids_to_test.append(module_id)

    extra_params = {}
    if Utils.is_not_empty(param):
        for token in param:
            kv = token.split("=", 1)
            if len(kv) == 2:
                key = kv[0]
                value = kv[1]
                extra_params[key] = value

    test_context = TestContext(
        cluster_name=cluster_name,
        aws_region=aws_region,
        admin_username=admin_username,
        admin_password=admin_password,
        extra_params=extra_params,
        module_set=module_set,
        module_ids=module_ids_to_test,
    )

    test_invoker = TestInvoker(test_context=test_context, module_ids=module_ids_to_test)

    test_invoker.invoke()
