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

from ideadatamodel import (
    exceptions,
    errorcodes,
    constants,
    SocaKeyValue,
    SocaUserInputParamMetadata,
    SocaUserInputParamType,
    SocaUserInputValidate,
    SocaUserInputChoice
)
from ideadatamodel.constants import CLICK_SETTINGS
from ideasdk.utils import Utils, ModuleMetadataHelper
from ideasdk.config.cluster_config_db import ClusterConfigDB
from ideasdk.config.cluster_config import ClusterConfig
from ideasdk.config.soca_config import SocaConfig
from ideasdk.context import SocaCliContext

import ideaadministrator
from ideaadministrator.app_utils import AdministratorUtils
from ideaadministrator.app_props import AdministratorProps
from ideaadministrator.app.config_generator import ConfigGenerator
from ideaadministrator.app.patch_helper import PatchHelper
from ideaadministrator.app.upload_helper import UploadHelper
from ideaadministrator.app.vpc_endpoints_helper import VpcEndpointsHelper
from ideaadministrator.app.aws_service_availability_helper import AwsServiceAvailabilityHelper
from ideaadministrator.app.cluster_prefix_list_helper import ClusterPrefixListHelper
from ideaadministrator.app.directory_service_helper import DirectoryServiceHelper

from prettytable import PrettyTable
import os
import sys
import click
import requests
import warnings
from rich.table import Table
from rich.console import Console
import time
import botocore.exceptions


@click.group(context_settings=CLICK_SETTINGS)
@click.version_option(version=ideaadministrator.__version__)
def main():
    """
    IDEA Administrator - install, deploy and manage your clusters

    \b
    * Deploy/Install IDEA from scratch
    ./res-admin.sh quick-setup

    \b
    * Deploy/Install IDEA using existing resources running on your AWS account
    ./res-admin.sh quick-setup --existing-resources

    * For all other operations (update/delete/check config...) please refer to the help section below
    """
    pass


@click.group()
def config():
    """
    configuration management options
    """
    pass


@click.group()
def cdk():
    """
    cdk app
    """
    pass

@click.group()
def directoryservice():
    """
    directory service utilities
    """
    pass


@click.group()
def utils():
    """
    cluster configuration utilities
    """
    pass


@utils.group()
def vpc_endpoints():
    """
    vpc endpoint utilities
    """
    pass


@utils.group()
def cluster_prefix_list():
    """
    cluster prefix list utilities
    """
    pass


@config.command('update', context_settings=CLICK_SETTINGS)
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--force', is_flag=True, help='Skip all confirmation prompts.')
@click.option('--overwrite', is_flag=True, help='Overwrite existing db config entries. '
                                                'Default behavior is to skip if the config entry exists.')
@click.option('--key-prefix', help='Update configuration for the keys matching the given key prefix.')
@click.option('--config-dir', help='Path to Config Directory; Uses default location if not provided')
@click.option('--module-set', help='Name of the ModuleSet. Default: default')
def config_update(cluster_name: str, aws_profile: str, aws_region: str, force: bool, overwrite: bool, key_prefix: str, config_dir: str, module_set: str):
    """
    update configuration from local file system to cluster settings dynamodb table
    """

    context = SocaCliContext()

    if Utils.is_empty(module_set):
        module_set = constants.DEFAULT_MODULE_SET

    values = {
        'cluster_name': cluster_name,
        'aws_profile': aws_profile,
        'aws_region': aws_region
    }
    config_generator = ConfigGenerator(values)

    if Utils.is_not_empty(config_dir):
        cluster_config_dir = os.path.join(config_dir, 'config')
        if not os.path.isdir(cluster_config_dir):
            context.error(f'{cluster_config_dir} does not exist')
            raise SystemExit
    else:
        cluster_config_dir = config_generator.get_cluster_config_dir()

    local_config_dict = config_generator.read_config_from_files(config_dir=cluster_config_dir)
    local_config = SocaConfig(config=local_config_dict)

    # perform a basic sanity check to see if the config in config dir is indeed the configuration for the expected cluster/aws region
    # this scenario is more likely to happen when using the --config-dir option
    #  where the configurations in the provided config dir does not match given --cluster-name and --aws-region
    cluster_module_id = local_config.get_string(f'global-settings.module_sets.{module_set}.cluster.module_id', required=True)
    local_config_cluster_name = local_config.get_string(f'{cluster_module_id}.cluster_name', required=True)
    if local_config_cluster_name != cluster_name:
        raise exceptions.cluster_config_error(f'local configuration in {cluster_config_dir} does not match the given cluster name: {cluster_name}')
    local_config_aws_region = local_config.get_string(f'{cluster_module_id}.aws.region', required=True)
    if local_config_aws_region != aws_region:
        raise exceptions.cluster_config_error(f'local configuration in {cluster_config_dir} does not match the given aws region: {aws_region}')

    def read_local_config_entries():
        context.info(f'reading cluster settings from {cluster_config_dir} ...')
        config_entries_ = config_generator.convert_config_to_key_value_pairs(key_prefix=key_prefix, path=cluster_config_dir)
        table = PrettyTable(['Key', 'Value'])
        table.align = 'l'
        for entry in config_entries_:
            key = Utils.get_value_as_string('key', entry, '-')
            value = Utils.get_any_value('value', entry, '-')
            if isinstance(value, list):
                value = Utils.to_yaml(value)
            table.add_row([
                key,
                value
            ])
        print(table)
        return config_entries_

    config_entries = read_local_config_entries()
    if not force:
        while True:
            result = context.prompt(
                message='Are you sure you want to update cluster settings db with above configuration from local file system?',
                default='Yes',
                choices=['Yes', 'Reload Changes', 'Exit']
            )
            if result == 'Exit':
                context.info('Aborted!')
                raise SystemExit
            elif result == 'Reload Changes':
                config_entries = read_local_config_entries()
            else:
                break

    local_config_dynamodb_kms_key_id = local_config.get_string(f'{cluster_module_id}.dynamodb.kms_key_id', required=False, default=None)

    cluster_config_db = ClusterConfigDB(
        cluster_name=config_generator.get_cluster_name(),
        aws_region=config_generator.get_aws_region(),
        aws_profile=config_generator.get_aws_profile(),
        dynamodb_kms_key_id=local_config_dynamodb_kms_key_id,
        create_database=True
    )
    if config_dir:
        modules = config_generator.read_modules_from_files(cluster_config_dir)
    else:
        modules = config_generator.read_modules_from_files()
    cluster_config_db.sync_modules_in_db(modules)
    cluster_config_db.sync_cluster_settings_in_db(config_entries, overwrite)


@config.command('set', context_settings=CLICK_SETTINGS)
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
@click.argument('entries', required=True, nargs=-1)
def set_config(cluster_name: str, aws_profile: str, aws_region: str, force: bool, entries):
    """
    set config entries on the dynamodb table, this does not change configurations in local file system

    \b
    entry must be of below format: Key=KEY_NAME,Type=[str|int|float|bool|list<str>|list<int>|list<float>|list<bool>],Value=[VALUE|[VALUE1,VALUE2,...]] ...
    config key names cannot contain: comma(,), colon(:)

    Examples:

    \b
    1) To set a string config type:
    ./res-admin.sh config set Key=global-settings.string_val,Type=string,Value=stringcontent --cluster-name YOUR_CLUSTER_NAME --aws-region YOUR_AWS_REGION

    \b
    2) To set an integer config type:
    ./res-admin.sh config set Key=global-settings.int_val,Type=int,Value=12 --cluster-name YOUR_CLUSTER_NAME --aws-region YOUR_AWS_REGION

    \b
    3) To set a config with list of strings:
    ./res-admin.sh config set "Key=my_config.string_list,Type=list<str>,Value=value1,value2" --cluster-name YOUR_CLUSTER_NAME --aws-region YOUR_AWS_REGION

    \b
    4) Update multiple config entries:
    ./res-admin.sh config set Key=global-settings.string_val,Type=string,Value=stringcontent \\
                               "Key=global-settings.integer_list,Type=list<int>,Value=1,2" \\
                               "Key=global-settings.string_list,Type=list<str>,Value=str1,str2" \\
                               --cluster-name YOUR_CLUSTER_NAME \\
                               --aws-region YOUR_AWS_REGION
    """

    config_entries = []
    for index, entry in enumerate(entries):
        tokens = entry.split(',', 2)
        key = tokens[0].split('Key=')[1].strip()
        data_type = tokens[1].split('Type=')[1].strip()
        value = tokens[2].split('Value=')[1].strip()

        if Utils.is_empty(key):
            raise exceptions.cluster_config_error(f'[{index}] Key is required')
        if ',' in key or ':' in key:
            raise exceptions.cluster_config_error(f'[{index}] Invalid Key: {key}. comma(,) and colon(:) are not allowed in key names.')
        if Utils.is_empty(data_type):
            raise exceptions.cluster_config_error(f'[{index}] Type is required')

        is_list = False
        if data_type in ('str', 'string'):
            data_type = 'str'
        elif data_type in ('int', 'integer'):
            data_type = 'int'
        elif data_type in ('bool', 'boolean'):
            data_type = 'bool'
        elif data_type in ('float', 'decimal'):
            data_type = 'float'
        elif data_type in ('list<str>', 'list<string>'):
            data_type = 'str'
            is_list = True
        elif data_type in ('list<int>', 'list<integer>'):
            data_type = 'int'
            is_list = True
        elif data_type in ('list<bool>', 'list<boolean>'):
            data_type = 'bool'
            is_list = True
        elif data_type in ('list<float>', 'list<decimal>'):
            data_type = 'float'
            is_list = True
        else:
            raise exceptions.cluster_config_error(f'[{index}] Type: {data_type} not supported')

        if is_list:
            tokens = value.split(',')
            value = []
            for token in tokens:
                if Utils.is_empty(token):
                    continue
                value.append(token.strip())
            if data_type == 'int':
                for val in value:
                    if not Utils.is_int(val):
                        raise exceptions.cluster_config_error(f'[{index}] Value: {value} is not a valid list<{data_type}>')
                value = Utils.get_as_int_list(value)
            elif data_type == 'float':
                for val in value:
                    if not Utils.is_float(val):
                        raise exceptions.cluster_config_error(f'[{index}] Value: {value} is not a valid list<{data_type}>')
                value = Utils.get_as_float_list(value)
            elif data_type == 'int':
                value = Utils.get_as_bool_list(value)
            else:
                value = Utils.get_as_string_list(value)
        else:
            if data_type == 'int':
                if not Utils.is_int(value):
                    raise exceptions.cluster_config_error(f'[{index}] Value: {value} is not a valid {data_type}')
                value = Utils.get_as_int(value)
            elif data_type == 'float':
                if not Utils.is_float(value):
                    raise exceptions.cluster_config_error(f'[{index}] Value: {value} is not a valid {data_type}')
                value = Utils.get_as_float(value)
            elif data_type == 'bool':
                value = Utils.get_as_bool(value)
            else:
                value = Utils.get_as_string(value)

        config_entries.append({
            'key': key,
            'value': value
        })

    context = SocaCliContext()

    table = PrettyTable(['Key', 'Value'])
    table.align = 'l'
    for config_entry in config_entries:
        key = Utils.get_value_as_string('key', config_entry, '-')
        value = Utils.get_any_value('value', config_entry, '-')
        if isinstance(value, list):
            value = Utils.to_yaml(value)
        table.add_row([key, value])

    print(table)
    if not force:
        confirm = context.prompt('Are you sure you want to update above config entries?')
        if not confirm:
            context.info('Abort!')
            raise SystemExit

    db = ClusterConfigDB(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile
    )
    for config_entry in config_entries:
        db.set_config_entry(config_entry['key'], config_entry['value'])


@config.command('export', context_settings=CLICK_SETTINGS)
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--export-dir', help='Export Directory. Defaults to: ~/.idea/clusters/<cluster-name>/<aws-region>/config')
def export_config(cluster_name: str, aws_profile: str, aws_region: str, export_dir: str):
    """
    export configuration
    """

    if Utils.is_empty(export_dir):
        props = AdministratorProps()
        cluster_dir = props.cluster_dir(cluster_name)
        cluster_region_dir = props.cluster_region_dir(cluster_dir, aws_region)
        export_dir = os.path.join(cluster_region_dir, 'config')

    if Utils.is_dir(export_dir):
        files = os.listdir(export_dir)
        applicable_files = []
        for file in files:
            if file == '.DS_Store':
                continue
            applicable_files.append(file)

        if len(applicable_files) > 0:
            raise exceptions.general_exception(f'export directory: {export_dir} already exists and can cause merge conflicts. '
                                               f'backup your existing configuration to another directory and try again.')

    db = ClusterConfigDB(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile
    )
    print(f'exporting config from db to {export_dir} ...')
    os.makedirs(export_dir, exist_ok=True)
    cluster_config = db.build_config_from_db()
    config_dict = cluster_config.as_dict()

    modules = db.get_cluster_modules()

    idea_config = {
        'modules': []
    }
    for module in modules:
        module_id = module['module_id']
        module_name = module['name']
        module_type = module['type']
        module_export_dir = os.path.join(export_dir, module_id)
        os.makedirs(module_export_dir, exist_ok=True)
        module_settings = Utils.get_value_as_dict(module_id, config_dict)
        module_settings_file = os.path.join(module_export_dir, 'settings.yml')
        with open(module_settings_file, 'w') as f:
            f.write(Utils.to_yaml(module_settings))
        idea_config['modules'].append({
            'name': module_name,
            'id': module_id,
            'type': module_type,
            'config_files': ['settings.yml']
        })

    with open(os.path.join(export_dir, 'idea.yml'), 'w') as f:
        f.write(Utils.to_yaml(idea_config))


@config.command('diff', context_settings=CLICK_SETTINGS)
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--config-dir', help='Path to local config folder; default location will be used if none provided')
def diff_config(cluster_name: str, aws_profile: str, aws_region: str, config_dir: str):
    """
    diff configuration files between the latest config and the config in the db
    """

    props = AdministratorProps()
    if Utils.is_empty(config_dir):
        cluster_home = props.cluster_dir(cluster_name)
        cluster_region_dir = props.cluster_region_dir(cluster_home, aws_region)
        cluster_config_dir = os.path.join(cluster_region_dir, 'config')
        print_using_default_warning('Configuration Directory', cluster_config_dir)

    db = ClusterConfigDB(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile
    )

    db_config_entries = {}
    config_entries = db.get_config_entries()

    for entry in config_entries:
        db_config_entries[Utils.get_value_as_string('key', entry)] = Utils.get_value_as_string('value', entry, '-')

    local_config_entries = {}
    values = {
        'cluster_name': cluster_name,
        'aws_profile': aws_profile,
        'aws_region': aws_region
    }
    config_generator = ConfigGenerator(values)
    local_config = config_generator.get_config_local(config_dir)

    for entry in local_config:
        local_config_entries[Utils.get_value_as_string('key', entry)] = Utils.get_value_as_string('value', entry, '-')

    set1 = set(local_config_entries.items())
    set2 = set(db_config_entries.items())

    set_x = set2 - set1
    set_y = set1 - set2

    table = Table()
    table.add_column("Key", justify="left", style="cyan", no_wrap=False)
    table.add_column("Old Value", justify="left", style="red", no_wrap=False)
    table.add_column("New Value", justify="left", style="green", no_wrap=False)
    table.add_column("Status", justify="left", style="magenta", no_wrap=False)

    rows = []

    for item in set_x:
        if item[0] in local_config_entries:
            rows.append((item[0], item[1], local_config_entries.get(item[0]), 'MODIFIED'))
        else:
            rows.append((item[0], item[1], 'n/a', 'DELETED'))
    for item in set_y:
        if item[0] in db_config_entries:
            continue
        rows.append((item[0], 'n/a', item[1], 'ADDED'))

    for row in sorted(rows):
        table.add_row(row[0], row[1], row[2], row[3])

    console = Console()
    console.print(table)


@config.command('show', context_settings=CLICK_SETTINGS)
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('-q', '--query', help='Search Query for configuration entries. Accepts a regular expression.')
@click.option('--format', 'output_format', help='Output format. One of [table, yaml, raw]. Default: table')
def show_config(cluster_name: str, aws_profile: str, aws_region: str, query: str, output_format: str):
    """
    show current configuration from dynamodb table for the deployed environment (as yaml)

    this can be different from configurations in local file system
    """
    cluster_config_db = ClusterConfigDB(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile
    )
    if output_format == 'yaml':
        cluster_config = cluster_config_db.build_config_from_db(query=query)
        print(cluster_config.as_yaml())
    elif output_format == 'raw':
        entries = cluster_config_db.get_config_entries(query=query)
        for entry in entries:
            value = entry.get('value')
            if value is not None:
                print(str(value))
    else:
        config_entries = cluster_config_db.get_config_entries(query=query)
        table = PrettyTable(['Key', 'Value', 'Version'])
        table.align = 'l'
        for entry in config_entries:
            key = Utils.get_value_as_string('key', entry, '-')
            value = Utils.get_any_value('value', entry, '-')
            if isinstance(value, list):
                value = Utils.to_yaml(value)
            version = Utils.get_value_as_int('version', entry, 0)
            table.add_row([
                key,
                value,
                version
            ])
        print(table)


@config.command('delete', context_settings=CLICK_SETTINGS)
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.argument('config-key-prefixes', nargs=-1, required=True)
def delete_config(cluster_name: str, aws_profile: str, aws_region: str, config_key_prefixes):
    """
    delete all configuration entries for a given config key prefix.

    to delete all configuration entries for alb.listener_rules.*, run:
    res-admin config delete alb.listener_rules.
    """
    db = ClusterConfigDB(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile
    )
    for config_key_prefix in config_key_prefixes:
        config_key_prefix = config_key_prefix.strip()
        db.delete_config_entries(config_key_prefix)


@click.command('patch')
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--package-uri', help='S3 package URI or package file path on local file system')
@click.option('--component', help='Component name')
@click.option('--instance-selector', help='Can be one of: [all, one]')
@click.option('--patch-command', help='Patch Command')
@click.option('--force', is_flag=True, help='Skip all confirmation prompts')
@click.argument('module', required=True)
def patch_module(cluster_name: str, aws_region: str, aws_profile: str, package_uri: str, component: str, instance_selector: str, force: bool, patch_command: str, module: str):
    """
    patch application module with the current release

    only supported for modules with type = 'app'
    """

    PatchHelper(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile,
        package_uri=package_uri,
        component=component,
        instance_selector=instance_selector,
        module_id=module,
        force=force,
        patch_command=patch_command
    ).apply()

@click.command('upload')
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--package-uri', help='S3 package URI or package file path on local file system')
@click.argument('module', required=True)
def upload_package(cluster_name: str, aws_region: str, aws_profile: str, package_uri: str, module: str):
    """
    upload application package to staging buckeet
    """

    UploadHelper(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile,
        package_uri=package_uri,
        module_id=module,
    ).apply()


@click.command('check-cluster-status')
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--wait', is_flag=True, help='Wait until all cluster endpoints are healthy.')
@click.option('--wait-timeout', default=900, help='Wait timeout in seconds. Default: 900 (15 mins)')
@click.option('--debug', is_flag=True, help='Print debug messages')
@click.option('--module-set', help='Name of the ModuleSet. Default: default')
def check_cluster_status(cluster_name: str, aws_region: str, aws_profile: str, wait: bool, wait_timeout: int, debug: bool, module_set: str):
    """
    check status for all applicable cluster endpoints
    """

    def check_status(endpoint_url):
        def get_status() -> bool:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    result = requests.get(url=endpoint_url, verify=False)  # nosec B501
                    if debug:
                        print(f'{endpoint_url} - {result.status_code} - {Utils.to_json(result.text)}')
                    if result.status_code == 200:
                        return True
                    else:
                        return False
            except Exception as e:
                if debug:
                    print(f'{e}')
                return False

        return get_status

    cluster_config = ClusterConfig(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile,
        module_set=module_set
    )

    context = SocaCliContext()
    module_metadata = ModuleMetadataHelper()

    cluster_endpoint = cluster_config.get_cluster_external_endpoint()
    cluster_modules = cluster_config.db.get_cluster_modules()

    endpoints = []

    for cluster_module in cluster_modules:
        module_id = cluster_module['module_id']
        module_name = cluster_module['name']
        module_type = cluster_module['type']
        if module_type == constants.MODULE_TYPE_APP:
            url = f'{cluster_endpoint}/{module_id}/healthcheck'
            endpoints.append({
                'name': module_metadata.get_module_title(module_name),
                'endpoint': url,
                'check_status': check_status(url)
            })

    current_time = Utils.current_time_ms()
    end_time = current_time + (wait_timeout * 1000)
    fail_count = 0
    keyboard_interrupt = False

    while current_time < end_time:

        context.info(f'checking endpoint status for cluster: {cluster_name}, url: {cluster_endpoint} ...')

        table = PrettyTable(['Module', 'Endpoint', 'Status'])
        table.align = 'l'

        fail_count = 0
        for endpoint in endpoints:
            success = endpoint['check_status']()
            if success:
                status = 'SUCCESS'
            else:
                status = 'FAIL'
                fail_count += 1

            table.add_row([
                endpoint['name'],
                endpoint['endpoint'],
                status
            ])

        print(table)

        if not wait:
            break

        if fail_count == 0:
            break

        print('failed to verify all cluster endpoints. wait ... (Press Ctrl + C to exit) ')
        try:
            time.sleep(60)
        except KeyboardInterrupt:
            keyboard_interrupt = True
            print('Check-endpoint status aborted.')
            break
        current_time = Utils.current_time_ms()

    if not keyboard_interrupt:
        if wait and current_time >= end_time:
            context.warning('check endpoint status timed-out. please verify your cluster\'s External ALB Security Group configuration and check correct ingress rules have been configured.')

        if fail_count > 0:
            raise SystemExit(1)


@click.command()
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--aws-profile', help='AWS Profile Name')
def list_modules(cluster_name: str, aws_region: str, aws_profile: str):
    """
    list all modules for a cluster
    """
    db = ClusterConfigDB(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile
    )
    modules = db.get_cluster_modules()
    table = PrettyTable(['Title', 'Name', 'Module ID', 'Type', 'Stack Name', 'Version', 'Status'])
    table.align = 'l'
    for module in modules:
        table.add_row([
            Utils.get_value_as_string('title', module),
            Utils.get_value_as_string('name', module),
            Utils.get_value_as_string('module_id', module),
            Utils.get_value_as_string('type', module),
            Utils.get_value_as_string('stack_name', module, '-'),
            Utils.get_value_as_string('version', module, '-'),
            Utils.get_value_as_string('status', module)
        ])
    print(table)


@click.command()
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--module-set', help='Name of the ModuleSet. Default: default')
def show_connection_info(cluster_name: str, aws_region: str, aws_profile: str, module_set: str):
    """
    print cluster connection information
    """
    cluster_config = ClusterConfig(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile,
        module_set=module_set
    )

    connection_info_entries = []

    cluster_modules = cluster_config.db.get_cluster_modules()

    cluster_endpoint = cluster_config.get_cluster_external_endpoint()

    if Utils.is_not_empty(cluster_endpoint):
        for cluster_module in cluster_modules:
            module_name = cluster_module['name']
            module_id = cluster_module['module_id']
            module_status = cluster_module['status']
            if module_status != 'deployed':
                continue
            if module_name == constants.MODULE_CLUSTER_MANAGER:
                connection_info_entries.append({
                    'key': 'Web Portal',
                    'value': cluster_endpoint,
                    'weight': 0
                })
            elif module_name == constants.MODULE_BASTION_HOST:
                key_pair_name = cluster_config.get_string('cluster.network.ssh_key_pair')
                ip_address = cluster_config.get_string(f'{module_id}.public_ip')
                if Utils.is_empty(ip_address):
                    ip_address = cluster_config.get_string(f'{module_id}.private_ip')
                if Utils.is_not_empty(ip_address):
                    base_os = cluster_config.get_string(f'{module_id}.base_os', required=True)
                    ec2_username = AdministratorUtils.get_ec2_username(base_os)
                    connection_info_entries.append({
                        'key': 'Bastion Host (SSH Access)',
                        'value': f'ssh -i ~/.ssh/{key_pair_name}.pem {ec2_username}@{ip_address}',
                        'weight': 1
                    })

                instance_id = cluster_config.get_string(f'{module_id}.instance_id')
                if Utils.is_not_empty(instance_id):
                    aws_partition = cluster_config.get_string('cluster.aws.partition', required=True)
                    connection_manager_url = AdministratorUtils.get_session_manager_url(aws_partition, aws_region, instance_id)
                    connection_info_entries.append({
                        'key': 'Bastion Host (Session Manager URL)',
                        'value': connection_manager_url,
                        'weight': 2
                    })

    context = SocaCliContext()

    if len(connection_info_entries) > 0:

        connection_info_entries.sort(key=lambda x: x['weight'])
        for entry in connection_info_entries:
            key = entry['key']
            value = entry['value']
            context.print(f'{key}: {value}')
    else:
        context.error(f'No connection information found for cluster: {cluster_name}. Is the cluster deployed?')


@click.command()
@click.option('--no-banner', is_flag=True, help='Do not print graphics and additional information')
def about(no_banner: bool):
    """
    print IDEA release version info
    """
    props = AdministratorProps()
    dev_mode = props.is_dev_mode()
    if no_banner:
        tokens = [
            'Engineering Studio on AWS',
            f'Version: v{ideaadministrator.__version__}'
        ]
        if dev_mode:
            tokens.append('(Developer Mode)')
        print(', '.join(tokens))
    else:
        context = SocaCliContext()
        meta_info = [
            SocaKeyValue(key='Version', value=ideaadministrator.__version__)
        ]
        if dev_mode:
            meta_info.append(SocaKeyValue(key='(Developer Mode)'))
        context.print_banner(meta_info=meta_info)


def print_using_default_warning(arg: str, path: str, cli: SocaCliContext = None):
    if cli is None:
        cli = SocaCliContext()
    cli.warning(f'WARNING: {arg} was not specified; Using default location: {path}')


@vpc_endpoints.command('service-info', context_settings=CLICK_SETTINGS)
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--aws-profile', help='AWS Profile Name')
def vpc_endpoints_service_info(aws_region: str, aws_profile: str):
    """
    print available vpc endpoint services in the region
    """
    vpc_endpoint_helper = VpcEndpointsHelper(
        aws_region=aws_region,
        aws_profile=aws_profile
    )
    vpc_endpoint_helper.print_vpc_endpoint_services()


@utils.command(context_settings=CLICK_SETTINGS)
def aws_services():
    """
    print all AWS services (required and optional) used by IDEA
    """
    helper = AwsServiceAvailabilityHelper()
    helper.print_idea_services()


@utils.command('check-aws-services', context_settings=CLICK_SETTINGS)
@click.option('--aws-profile', help='AWS Profile Name')
@click.argument('AWS_REGION', nargs=-1, required=True)
def check_aws_services(aws_profile: str, aws_region):
    """
    check and print availability of AWS services required by IDEA for a given AWS region
    """
    helper = AwsServiceAvailabilityHelper(aws_profile=aws_profile)
    helper.print_availability_matrix(aws_regions=list(aws_region))


@cluster_prefix_list.command('show', context_settings=CLICK_SETTINGS)
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--aws-profile', help='AWS Profile Name')
def cluster_prefix_list_show(cluster_name: str, aws_region: str, aws_profile: str):
    """
    print all CIDR entries in the cluster prefix list
    """
    entries = ClusterPrefixListHelper(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile
    ).list_entries()

    table = PrettyTable(['CIDR', 'Description'])
    table.align = 'l'
    for entry in entries:
        cidr = Utils.get_value_as_string('cidr', entry)
        description = Utils.get_value_as_string('description', entry, '-')
        table.add_row([cidr, description])
    print(table)


@cluster_prefix_list.command('add-entry', context_settings=CLICK_SETTINGS)
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--cidr', required=True, help='CIDR Entry')
@click.option('--description', required=True, help='CIDR Entry Description')
def cluster_prefix_list_add_entry(cluster_name: str, aws_region: str, aws_profile: str, cidr: str, description: str):
    """
    add CIDR entry to cluster prefix list
    """
    ClusterPrefixListHelper(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile
    ).add_entry(cidr=cidr, description=description)


@cluster_prefix_list.command('remove-entry', context_settings=CLICK_SETTINGS)
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--cidr', required=True, help='CIDR Entry')
def cluster_prefix_list_remove_entry(cluster_name: str, aws_region: str, aws_profile: str, cidr: str):
    """
    remove CIDR entry from cluster prefix list
    """
    ClusterPrefixListHelper(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile
    ).remove_entry(cidr=cidr)


@directoryservice.command('create-service-account-secrets', context_settings=CLICK_SETTINGS)
@click.option('--cluster-name', required=True, help='Cluster Name')
@click.option('--aws-region', required=True, help='AWS Region')
@click.option('--aws-profile', help='AWS Profile Name')
@click.option('--username', help='Service Account Username')
@click.option('--password', help='Service Account Password')
@click.option('--kms-key-id', help='KMS Key ID')
@click.option('--purpose', help='Account Purpose (e.g. service-account, clusteradmin)')
def ds_create_service_secrets(cluster_name: str, aws_region: str, aws_profile: str,
                              username: str, password: str, kms_key_id: str, purpose: str):
    """
    create service account secrets for directory service
    """

    context = SocaCliContext()

    helper = DirectoryServiceHelper(
        cluster_name=cluster_name,
        aws_region=aws_region,
        aws_profile=aws_profile
    )

    if Utils.is_any_empty(username, password):
        ask_result = context.ask(
            title='Directory Service - Service Account Credentials',
            description='Enter the account credentials to create secrets in AWS Secrets Manager with applicable tags',
            questions=[
                SocaUserInputParamMetadata(
                    name='purpose',
                    title='Purpose',
                    description="Enter account purpose",
                    data_type='str',
                    param_type=SocaUserInputParamType.SELECT,
                    multiple=False,
                    choices=[
                        SocaUserInputChoice(title='clusteradmin    - Used for initial login/configuration of the IDEA cluster', value='clusteradmin'),
                        SocaUserInputChoice(title='service-account - Used for binding to the Active Directory/LDAP', value='service-account')
                    ],
                    default=purpose,
                    validate=SocaUserInputValidate(required=True)
                ),
                SocaUserInputParamMetadata(
                    name='username',
                    title='Username',
                    description='Enter account username',
                    data_type='str',
                    param_type=SocaUserInputParamType.TEXT,
                    default=username,
                    validate=SocaUserInputValidate(required=True)
                ),
                SocaUserInputParamMetadata(
                    name='password',
                    title='Password',
                    description='Enter account password',
                    data_type='str',
                    param_type=SocaUserInputParamType.PASSWORD,
                    default=username,
                    validate=SocaUserInputValidate(required=True)
                )
            ])
        purpose = ask_result['purpose']
        username = ask_result['username']
        password = ask_result['password']

    with context.spinner(f'creating {purpose} secrets ...'):
        secret_arns = helper.create_service_account_secrets(
            purpose=purpose,
            username=username,
            password=password,
            kms_key_id=kms_key_id
        )

    credentials_secret_arn = secret_arns['credentials_secret_arn']

    context.success(f'directory service {purpose} secrets created successfully: ')
    print(f'Account Purpose: {purpose}')
    print(f'Credentials Secret ARN: {credentials_secret_arn}')



main.add_command(cdk)
main.add_command(config)
main.add_command(list_modules)
main.add_command(show_connection_info)
main.add_command(patch_module)
main.add_command(upload_package)
main.add_command(check_cluster_status)
main.add_command(about)
main.add_command(utils)
main.add_command(directoryservice)


def main_wrapper():
    success = True
    exit_code = 0

    try:

        args = sys.argv[1:]

        has_params = False
        if len(args) > 0:
            if len(args) == 1:
                param = args[0]
                has_params = Utils.is_not_empty(param)
            elif len(args) > 1:
                has_params = True

        if has_params:
            main(args)
        else:
            main(['-h'])

    except exceptions.SocaException as e:
        if e.error_code == errorcodes.USER_INPUT_FLOW_INTERRUPT:
            pass
        elif e.error_code == errorcodes.CLUSTER_CONFIG_NOT_INITIALIZED:
            click.secho(f'{e}. Is the cluster configuration synced?', fg='red', bold=True)
            success = False
        elif e.error_code in (errorcodes.CONFIG_ERROR,
                              errorcodes.USER_INPUT_FLOW_ERROR,
                              errorcodes.INTEGRATION_TEST_FAILED):
            click.secho(f'{e}', fg='red', bold=True)
            success = False
        else:
            raise e
    except botocore.exceptions.ProfileNotFound as e:
        click.secho(f'{e}', fg='red', bold=True)
        success = False
    except SystemExit as e:
        success = e.code == 0
        exit_code = e.code
    except Exception as e:
        click.secho(f'Command failed with error: {e}', fg='red', bold=True)
        raise e

    if not success:
        if exit_code == 0:
            exit_code = 1
        sys.exit(exit_code)


# used only for local testing
if __name__ == '__main__':
    main_wrapper()
