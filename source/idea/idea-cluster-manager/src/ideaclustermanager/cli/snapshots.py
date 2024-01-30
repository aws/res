from ideadatamodel import constants, ApplySnapshotRequest, ApplySnapshotResult

from ideaclustermanager.cli import build_cli_context
import click

@click.group()
def snapshots():
    """
    snapshot management options
    """
    
@snapshots.command(context_settings=constants.CLICK_SETTINGS)
@click.option('--s3_bucket_name', required=True, help='S3 Bucket Name to retrieve the snapshot from')
@click.option('--snapshot_path', required=True, help='Path in the S3 bucket to retrieve the snapshot from')
def apply_snapshot(**kwargs):
    """
    apply snapshot
    """
    request = {
        'snapshot': {
            's3_bucket_name': kwargs.get('s3_bucket_name'),
            'snapshot_path': kwargs.get('snapshot_path')
        }
    }
    
    context = build_cli_context()
    result = context.unix_socket_client.invoke_alt(
        namespace='Snapshots.ApplySnapshot',
        payload=ApplySnapshotRequest(**request),
        result_as=ApplySnapshotResult
    )
    print(result)