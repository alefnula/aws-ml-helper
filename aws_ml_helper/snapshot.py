__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '22 March 2018'
__copyright__ = 'Copyright (c)  2018 Viktor Kerkez'

import click
from tabulate import tabulate
from aws_ml_helper import boto
from aws_ml_helper.utils import name_from_tags
from botocore.exceptions import WaiterError


def get_snapshot(config, name):
    """Get snapshot by name"""
    ec2 = boto.resource('ec2', config)
    snapshot_list = list(ec2.snapshots.filter(
        Filters=[{'Name': 'tag:Name', 'Values': [name]}]
    ))
    if len(snapshot_list) == 0:
        click.secho(f'Snapshot "{name}" not found')
        return None
    elif len(snapshot_list) > 1:
        click.secho(f'Multiple snapshots with name "{name}" found.')
        return None
    return snapshot_list[0]


def snapshots(config):
    """List all snapshots

    Args:
        config (aws_ml_helper.config.Config): Configuration
    """
    ec2 = boto.resource('ec2', config)
    data = []
    for i in ec2.snapshots.filter(OwnerIds=[config.account]):
        data.append([
            name_from_tags(i.tags),
            i.id,
            i.state,
            i.volume_size,
            i.description
        ])
    print(tabulate(
        data, ['name', 'id', 'state', 'size', 'description'], 'fancy_grid'
    ))


def snapshot_create(config, volume_name, snapshot_name, default=False,
                    wait=False):
    """Create a snapshot from a volume

    Args:
        config (aws_ml_helper.config.Config): Configuration
        volume_name (str): Name of the volume
        snapshot_name (str): Desired snapshot name
        default (bool): Is this a default snapshot that should be saved in
            the configuration.
        wait (bool): Wait for the snapshot creation to complete
    """
    from aws_ml_helper.volume import get_volume
    volume = get_volume(config, volume_name)
    snapshot = volume.create_snapshot(
        Description=snapshot_name,
        TagSpecifications=[{
            'ResourceType': 'snapshot',
            'Tags': [{'Key': 'Name', 'Value': snapshot_name}]
        }]
    )
    if wait:
        while True:
            try:
                snapshot.wait_until_completed()
                break
            except WaiterError:
                pass

    if default:
        config.snapshot_id = snapshot.id
        config.save()
