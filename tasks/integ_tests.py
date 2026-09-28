#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import os
from typing import List, Optional

import invoke.exceptions
from invoke import Context, task

import tasks.idea as idea


def _run_component_integ_tests(
    c: Context,
    component_name: str,
    component_src: str,
    component_tests_src: str,
    package_name: str,
    params: List[str],
    capture_output: bool = False,
    keywords=None,
    cov_report=None,
    test_file=None,
) -> int:
    """
    Currently requires ~/.aws/credentials file to be setup in order to run due to boto being unable to use ~/.aws/config.
    """
    params.append(f"module={component_name}")
    if cov_report is not None and cov_report in (
        "term",
        "term-missing",
        "annotate",
        "html",
        "xml",
        "lcov",
    ):
        params.append(f"cov={package_name}")
        params.append(f"cov-report={cov_report}")

    return _run_integ_tests(
        c,
        component_name,
        component_tests_src,
        params,
        [component_src],
        capture_output,
        keywords,
        test_file
    )


def _run_integ_tests(
    c: Context,
    test_id: str,
    tests_src: str,
    params: List[str],
    additional_python_path: Optional[List[str]] = None,
    capture_output: bool = False,
    keywords=None,
    test_file=None,
    num_workers=None,
    marker_expr=None,
) -> int:
    """
    Currently requires ~/.aws/credentials file to be setup in order to run due to boto being unable to use ~/.aws/config.
    """
    test_params = []
    if params is not None:
        for param in params:
            kv = param.split("=")
            key = kv[0]
            value = None
            if len(kv) > 1:
                value = kv[1]
            test_params += [f"--{key}"]
            if value is not None:
                test_params += [value]

    idea.console.print_header_block(f"executing integ tests for: {test_id}")
    python_path = [
        idea.props.project_root_dir,
        idea.props.data_model_src,
        idea.props.sdk_src,
        idea.props.library_src,
        idea.props.datamodel_src,
        idea.props.test_utils_src,
    ]
    if tests_src not in python_path:
        python_path.append(tests_src)
    if additional_python_path:
        python_path = list(set(python_path + additional_python_path))

    with c.cd(tests_src):
        # Build the base command
        base_cmd = 'pytest -v -rx --log-cli-level=INFO --disable-warnings'
        
        # Add test file if specified, otherwise run all tests in the directory
        if test_file is not None:
            cmd = f'{base_cmd} {test_file} {" ".join(test_params)}'
        else:
            cmd = f'{base_cmd} {" ".join(test_params)}'
            
        if capture_output:
            cmd = f"{cmd} --capture=tee-sys"
        if keywords is not None:
            cmd = f'{cmd} -k "{keywords}"'
        if marker_expr is not None:
            cmd = f'{cmd} -m "{marker_expr}"'
        if num_workers is not None:
            cmd = f'{cmd} -n {num_workers} --dist=loadgroup'
        idea.console.info(f"> {cmd}")

        try:
            result = c.run(cmd, env={"PYTHONPATH": os.pathsep.join(python_path)})
            return result.exited
        except SystemExit as e:
            return e.code
        except invoke.exceptions.UnexpectedExit:
            return 1
        except Exception as e:
            print(e)
            return 1


@task(iterable=["params"])
def cluster_manager(
    c, keywords=None, params=None, capture_output=False, cov_report=None
):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run cluster-manager integ tests
    """
    exit_code = _run_component_integ_tests(
        c=c,
        component_name="cluster-manager",
        component_src=idea.props.cluster_manager_src,
        component_tests_src=idea.props.administrator_integ_tests_dir,
        package_name="ideaadministrator",
        params=params,
        capture_output=capture_output,
        keywords=keywords,
        cov_report=cov_report,
        test_file="run_integ_tests.py",
    )
    raise SystemExit(exit_code)


@task(iterable=["params"])
def ad_sync(
    c, keywords=None, params=None, capture_output=False, cov_report=None
):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run ad-sync integ tests
    """
    exit_code = _run_component_integ_tests(
        c=c,
        component_name="ad-sync",
        component_src=idea.props.ad_sync_src,
        component_tests_src=idea.props.ad_sync_integ_tests_src,
        package_name="adsync",
        params=params,
        capture_output=capture_output,
        keywords=keywords,
        cov_report=cov_report,
        test_file="test_adsync.py",
    )
    raise SystemExit(exit_code)


@task(iterable=["params"])
def smoke(
    c, keywords=None, params=None, capture_output=False, cov_report=None,
    marker_expr=None,
):
    # type: (Context, str, List[str], bool, str, str) -> None
    """
    run smoke tests

    Pass --marker-expr "smoke_subset" to run only the single-OS (AL2023) subset
    (used by the per-commit pipeline); omit it to run the full OS matrix (nightly).
    """
    exit_code = _run_integ_tests(
        c=c,
        test_id="smoke",
        tests_src=idea.props.end_to_end_integ_tests_dir,
        params=params,
        capture_output=capture_output,
        keywords=keywords,
        test_file="test_smoke.py test_dcv_session_management.py",
        num_workers=22,
        marker_expr=marker_expr,
    )
    raise SystemExit(exit_code)


@task(iterable=["params"])
def api(
    c, keywords=None, params=None, capture_output=False, cov_report=None,
):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run API tests
    """
    exit_code = _run_integ_tests(
        c=c,
        test_id="api",
        tests_src=idea.props.api_tests_dir,
        params=params,
        capture_output=capture_output,
        keywords=keywords,
    )
    raise SystemExit(exit_code)


@task(iterable=["params"])
def vdc(
    c, keywords=None, params=None, capture_output=False, cov_report=None,
):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run vdc integ tests
    """
    exit_code = _run_integ_tests(
        c=c,
        test_id="vdc",
        tests_src=idea.props.end_to_end_integ_tests_dir,
        params=params,
        capture_output=capture_output,
        keywords=keywords,
        test_file="test_vdc.py",
        num_workers=2,
    )
    raise SystemExit(exit_code)


# Marker expression selected by each suite. The whole integration test tree is
# collected and filtered by these expressions, so suite membership is determined
# by the @pytest.mark.<suite> decorators on the tests, not by directory.
SUITE_MARKER_EXPR = {
    "dev": "dev",
    "nightly": "nightly and not scale and not gpu and not ui and not govcloud",
    "release": "release or nightly",
    "smart_retry": "smart_retry",
}

# Default xdist worker counts per suite.
# NOTE: the dev suite runs SERIALLY (num_workers=None). The API tests it collects
# toggle global backend-lambda state (set_backend_lambda_test_mode/dry_mode) on the
# shared environment, so running them in parallel makes those toggles race across
# workers and produces spurious "Unable to retrieve username" 401s. The pre-existing
# integ-tests.api task runs serially for the same reason. nightly/release tests are
# isolated per session/VDI and can parallelize.
# smart_retry runs SERIALLY because it mutates the global smart retry setting.
SUITE_NUM_WORKERS = {
    "dev": None,
    "nightly": 22,
    "release": 22,
    "smart_retry": None,
}


def _run_suite(
    c,
    suite,
    params=None,
    capture_output=False,
    keywords=None,
    marker_expr=None,
    num_workers=None,
):
    # type: (Context, str, List[str], bool, str, str, int) -> int
    """
    Run a marker-driven integration test suite (dev/nightly/release).

    marker_expr overrides the default suite expression for local debugging.
    """
    return _run_integ_tests(
        c=c,
        test_id=suite,
        tests_src=idea.props.integration_tests_dir,
        params=params,
        capture_output=capture_output,
        keywords=keywords,
        test_file=None,  # collect the whole tree, select by marker
        marker_expr=marker_expr or SUITE_MARKER_EXPR[suite],
        num_workers=num_workers or SUITE_NUM_WORKERS[suite],
    )


@task(iterable=["params"])
def dev(
    c, keywords=None, params=None, capture_output=False, marker_expr=None,
):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run the dev suite (fast per-commit checks: API + dry-run)
    """
    exit_code = _run_suite(
        c, "dev", params=params, capture_output=capture_output,
        keywords=keywords, marker_expr=marker_expr,
    )
    raise SystemExit(exit_code)


@task(iterable=["params"])
def nightly(
    c, keywords=None, params=None, capture_output=False, marker_expr=None,
):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run the nightly suite (full smoke + VDI lifecycle across the OS matrix)
    """
    exit_code = _run_suite(
        c, "nightly", params=params, capture_output=capture_output,
        keywords=keywords, marker_expr=marker_expr,
    )
    raise SystemExit(exit_code)


@task(iterable=["params"])
def release(
    c, keywords=None, params=None, capture_output=False, marker_expr=None,
):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run the release suite (comprehensive pre-release: scale, snapshot, all OS)
    """
    exit_code = _run_suite(
        c, "release", params=params, capture_output=capture_output,
        keywords=keywords, marker_expr=marker_expr,
    )
    raise SystemExit(exit_code)


@task(iterable=["params"])
def smart_retry(
    c, keywords=None, params=None, capture_output=False, marker_expr=None,
):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run the smart retry suite (mutates global state, must run after nightly)
    """
    exit_code = _run_suite(
        c, "smart_retry", params=params, capture_output=capture_output,
        keywords=keywords, marker_expr=marker_expr,
    )
    raise SystemExit(exit_code)
