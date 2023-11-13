from ideadatamodel import VirtualDesktopBaseOS, constants, VirtualDesktopEventType
from ideasdk.bootstrap import BootstrapUserDataBuilder, BootstrapPackageBuilder
from ideasdk.config.cluster_config import ClusterConfig
from ideasdk.context import BootstrapContext
import os


def build_and_upload_bootstrap_package(config: ClusterConfig, base_os: VirtualDesktopBaseOS, instance_type: str, session_id: str) -> str:
    bootstrap_context = BootstrapContext(
        config=config,
        module_name=constants.MODULE_VIRTUAL_DESKTOP_CONTROLLER,
        module_id='vdc',
        base_os=base_os.value,
        instance_type=instance_type
    )

    session_owner = 'test-session-owner'
    bootstrap_context.vars.session_owner = session_owner
    bootstrap_context.vars.idea_session_id = session_id
    if base_os != VirtualDesktopBaseOS.WINDOWS:
        escape_chars = '\\'
    else:
        escape_chars = '`'

    bootstrap_context.vars.dcv_host_ready_message = f'{{{escape_chars}"event_group_id{escape_chars}":{escape_chars}"{session_id}{escape_chars}",{escape_chars}"event_type{escape_chars}":{escape_chars}"{VirtualDesktopEventType.DCV_HOST_READY_EVENT}{escape_chars}",{escape_chars}"detail{escape_chars}":{{{escape_chars}"idea_session_id{escape_chars}":{escape_chars}"{session_id}{escape_chars}",{escape_chars}"idea_session_owner{escape_chars}":{escape_chars}"{session_owner}{escape_chars}"}}}}'

    tmp_dir = os.path.join('/Users/madbajaj/SOCA/Solution-for-scale-out-computing-on-aws/tests/modules/vdc/outputs/', 'dcv_host', session_id)
    components = [
        'virtual-desktop-host-linux'
    ]
    if base_os == VirtualDesktopBaseOS.WINDOWS:
        components = [
            'virtual-desktop-host-windows'
        ]

    bootstrap_package_archive_file = BootstrapPackageBuilder(
        bootstrap_context=bootstrap_context,
        source_directory='/Users/madbajaj/SOCA/Solution-for-scale-out-computing-on-aws/source/idea/idea-bootstrap',
        target_package_basename=f'dcv-host-{session_id}',
        components=components,
        tmp_dir=tmp_dir,
        force_build=True
    ).build()
    cluster_s3_bucket = config.get_string('cluster.cluster_s3_bucket', required=True)
    upload_key = f'idea/dcv_host/bootstrap/testing/{session_id}/{os.path.basename(bootstrap_package_archive_file)}'
    '''
    self.s3_client.upload_file(
        Bucket=cluster_s3_bucket,
        Filename=bootstrap_package_archive_file,
        Key=upload_key
    )
    '''
    return f's3://{cluster_s3_bucket}/{upload_key}'


def build_user_data(baseos: VirtualDesktopBaseOS, config: ClusterConfig, instance_type: str, session_id: str) -> str:
    install_commands = [
        '/bin/bash virtual-desktop-host-linux/setup.sh'
    ]
    if baseos == VirtualDesktopBaseOS.WINDOWS:
        install_commands = [
            'cd \"virtual-desktop-host-windows\"',
            'Import-Module .\\SetUp.ps1',
            'Set-Up'
        ]

    user_data_builder = BootstrapUserDataBuilder(
        base_os=baseos.value,
        aws_region=config.get_string('cluster.aws.region', required=True),
        bootstrap_package_uri=build_and_upload_bootstrap_package(config, baseos, instance_type, session_id),
        install_commands=install_commands
    )
    return user_data_builder.build()


cluster_config = ClusterConfig(
    cluster_name='idea-mbajaj',
    aws_region='us-west-2',
    module_id='vdc'
)

build_user_data(VirtualDesktopBaseOS.CENTOS7, cluster_config, 'g4dn.2xlarge', 'gpu-centos7')
build_user_data(VirtualDesktopBaseOS.RHEL7, cluster_config, 'g4dn.2xlarge', 'gpu-rhel7')
build_user_data(VirtualDesktopBaseOS.AMAZON_LINUX2, cluster_config, 'g4dn.2xlarge', 'gpu-al2')

build_user_data(VirtualDesktopBaseOS.CENTOS7, cluster_config, 'm5.xlarge', 'non-gpu-centos7')
build_user_data(VirtualDesktopBaseOS.RHEL7, cluster_config, 'm5.xlarge', 'non-gpu-rhel7')
build_user_data(VirtualDesktopBaseOS.AMAZON_LINUX2, cluster_config, 'm5.xlarge', 'non-gpu-al2')
build_user_data(VirtualDesktopBaseOS.WINDOWS, cluster_config, 'm5.xlarge', 'non-gpu-win')

