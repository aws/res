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
from typing import List


def _run_unit_tests(c: Context,
                    component_name: str,
                    component_src: str,
                    component_tests_src: str,
                    package_name: str,
                    params: List[str],
                    capture_output: bool = False,
                    keywords=None,
                    cov_report=None) -> int:
    test_params = []
    if params is not None:
        for param in params:
            kv = param.split('=')
            key = kv[0]
            value = None
            if len(kv) > 1:
                value = kv[1]
            test_params += [f'--{key}']
            if value is not None:
                test_params += [value]

    idea.console.print_header_block(f'executing unit tests for: {component_name}')
    python_path = [
        idea.props.project_root_dir,
        idea.props.data_model_src,
        idea.props.sdk_src,
        idea.props.test_utils_src
    ]
    if component_src not in python_path:
        python_path.append(component_src)
    if component_tests_src not in python_path:
        python_path.append(component_tests_src)

    with c.cd(component_tests_src):
        cmd = f'pytest -v --disable-warnings {" ".join(test_params)}'
        if capture_output:
            cmd = f'{cmd} --capture=tee-sys'
        if keywords is not None:
            cmd = f'{cmd} -k "{keywords}"'
        if cov_report is not None and cov_report in ('term', 'term-missing', 'annotate', 'html', 'xml', 'lcov'):
            cmd = f'{cmd} --cov {package_name} --cov-report {cov_report}'
        idea.console.info(f'> {cmd}')

        try:
            result = c.run(cmd, env={
                'PYTHONPATH': os.pathsep.join(python_path)
            })
            return result.exited
        except SystemExit as e:
            return e.code
        except invoke.exceptions.UnexpectedExit:
            return 1
        except Exception as e:
            print(e)
            return 1


@task(iterable=['params'])
def sdk(c, keywords=None, params=None, capture_output=False, cov_report=None):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run sdk unit tests
    """
    exit_code = _run_unit_tests(
        c=c,
        component_name='sdk',
        component_src=idea.props.sdk_src,
        component_tests_src=idea.props.sdk_tests_src,
        package_name='ideasdk',
        params=params,
        capture_output=capture_output,
        keywords=keywords,
        cov_report=cov_report
    )
    raise SystemExit(exit_code)


@task(iterable=['params'])
def cluster_manager(c, keywords=None, params=None, capture_output=False, cov_report=None):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run cluster-manager unit tests
    """
    exit_code = _run_unit_tests(
        c=c,
        component_name='cluster-manager',
        component_src=idea.props.cluster_manager_src,
        component_tests_src=idea.props.cluster_manager_tests_src,
        package_name='ideaclustermanager',
        params=params,
        capture_output=capture_output,
        keywords=keywords,
        cov_report=cov_report
    )
    raise SystemExit(exit_code)


@task(iterable=['params'])
def virtual_desktop_controller(c, keywords=None, params=None, capture_output=False, cov_report=None):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run virtual desktop controller unit tests
    """
    exit_code = _run_unit_tests(
        c=c,
        component_name='virtual-desktop-controller',
        component_src=idea.props.virtual_desktop_src,
        component_tests_src=idea.props.virtual_desktop_tests_src,
        package_name='ideavirtualdesktopcontroller',
        params=params,
        capture_output=capture_output,
        keywords=keywords,
        cov_report=cov_report
    )
    raise SystemExit(exit_code)


@task(iterable=['params'])
def administrator(c, keywords=None, params=None, capture_output=False, cov_report=None):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run administrator unit tests
    """
    exit_code = _run_unit_tests(
        c=c,
        component_name='administrator',
        component_src=idea.props.administrator_src,
        component_tests_src=idea.props.administrator_tests_src,
        package_name='ideaadministrator',
        params=params,
        capture_output=capture_output,
        keywords=keywords,
        cov_report=cov_report
    )
    raise SystemExit(exit_code)

@task(iterable=['params'])
def lambda_functions(c, keywords=None, params=None, capture_output=False, cov_report=None):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run administrator unit tests
    """
    exit_code = _run_unit_tests(
        c=c,
        component_name='lambda_functions',
        component_src=idea.props.lambda_functions_src,
        component_tests_src=idea.props.lambda_functions_tests_src,
        package_name='lambda_functions',
        params=params,
        capture_output=capture_output,
        keywords=keywords,
        cov_report=cov_report
    )
    raise SystemExit(exit_code)

@task(name='all', iterable=['params'], default=True)
def run_all(c, keywords=None, params=None, capture_output=False, cov_report=None):
    # type: (Context, str, List[str], bool, str) -> None
    """
    run unit tests for all components
    """
    components = [
        sdk,
        administrator,
        cluster_manager,
        virtual_desktop_controller,
        lambda_functions
    ]

    exit_code = 0
    for component_fn in components:
        try:
            component_fn(c, keywords, params, capture_output, cov_report)
        except SystemExit as e:
            if e.code != 0:
                exit_code = e.code

    raise SystemExit(exit_code)
