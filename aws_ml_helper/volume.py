__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '21 March 2018'
__copyright__ = 'Copyright (c)  2018 Viktor Kerkez'

import time
import click
from tabulate import tabulate
from aws_ml_helper import boto
from aws_ml_helper.utils import name_from_tags
from aws_ml_helper.instance import get_instance


def get_volume(config, name):
    """Returns a volume object with selected name or returns `None` if the
    volume is not found.

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Volume name

    Returns:
        Volume if found or None
    """
    ec2 = boto.resource('ec2', config)
    volume_list = list(ec2.volumes.filter(
        Filters=[{'Name': 'tag:Name', 'Values': [name]}]
    ))
    if len(volume_list) == 0:
        click.secho(f'Volume "{name}" not found')
        return None
    elif len(volume_list) > 1:
        click.secho(f'Multiple volumes with name "{name}" found.')
        return None
    return volume_list[0]


def volumes(config):
    """List volumes and their attributes

    Args:
        config (aws_ml_helper.config.Config): Configuration
    """
    ec2 = boto.resource('ec2', config)
    data = []
    for v in ec2.volumes.all():
        data.append([
            name_from_tags(v.tags),
            v.id,
            v.size,
            v.state,
            ', '.join([a['InstanceId'] for a in v.attachments])
        ])

    print(tabulate(
        data, ['name', 'id', 'size', 'state', 'attachments'],
        config.table_format
    ))


def volume_create(config, name, size=256, snapshot_name=None, wait=False):
    """Create an EBS volume.

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Name of the volume
        size (int): Volume size
        snapshot_name (str): Name of the snapshot from which the volume should
            be created
        wait (bool): Wait for the volume to become `available`
    """
    ec2 = boto.resource('ec2', config)
    from aws_ml_helper.snapshot import get_snapshot
    snapshot = get_snapshot(config, snapshot_name)
    snapshot_id = (snapshot and snapshot.id) or None
    volume = ec2.create_volume(
        AvailabilityZone=config.availability_zone,
        Size=size,
        SnapshotId=snapshot_id,
        VolumeType='gp2',
        TagSpecifications=[{
            'ResourceType': 'volume',
            'Tags': [{'Key': 'Name', 'Value': name}]
        }]
    )
    if wait:
        while volume.state != 'available':
            time.sleep(1)
            volume.reload()


def volume_attach(config, volume_name, instance_name, device='xvdh'):
    """Attach a volume to instance.

    Args:
        config (aws_ml_helper.config.Config): Configuration
        volume_name (str): Volume name
        instance_name (str): Instance name
        device (str): The device name
    """
    volume = get_volume(config, volume_name)
    instance = get_instance(config, instance_name)
    volume.attach_to_instance(
        Device=device,
        InstanceId=instance.id,
    )


def volume_detach(config, volume_name, instance_name, device='xvdh'):
    """Detach a volume from an instance.

    Args:
        config (aws_ml_helper.config.Config): Configuration
        volume_name (str): Volume name
        instance_name (str): Instance name
        device (str): The device name
    """
    volume = get_volume(config, volume_name)
    instance = get_instance(config, instance_name)
    volume.detach_from_instance(
        Device=device,
        Force=True,
        InstanceId=instance.id,
    )


def volume_delete(config, volume_name):
    """Delete a volume.

    Args:
        config (aws_ml_helper.config.Config): Configuration
        volume_name: Volume name
    """
    volume = get_volume(config, volume_name)
    volume.delete()
