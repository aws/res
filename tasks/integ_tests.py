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

import invoke.exceptions
import tasks.idea as idea
from invoke import task, Context
import os
from typing import List, Optional


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
        idea.props.test_utils_src,
    ]
    if tests_src not in python_path:
        python_path.append(tests_src)
    if additional_python_path:
        python_path = list(set(python_path + additional_python_path))

    with c.cd(tests_src):
        cmd = f'pytest -v --disable-warnings {test_file} {" ".join(test_params)}'
        if capture_output:
            cmd = f"{cmd} --capture=tee-sys"
        if keywords is not None:
            cmd = f'{cmd} -k "{keywords}"'
        if num_workers is not None:
            cmd = f'{cmd} -n {num_workers}'
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
def smoke(
    c, keywords=None, params=None, capture_output=False, cov_report=None,
):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run smoke tests
    """
    exit_code = _run_integ_tests(
        c=c,
        test_id="smoke",
        tests_src=idea.props.end_to_end_integ_tests_dir,
        params=params,
        capture_output=capture_output,
        keywords=keywords,
        test_file="smoke.py",
        num_workers=8,
    )
    raise SystemExit(exit_code)
