__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '20 October 2010'
__copyright__ = 'Copyright (c) 2010 Viktor Kerkez'

import click
from tabulate import tabulate
from aws_ml_helper import boto
from datetime import datetime, timedelta
from aws_ml_helper.instance import run
from aws_ml_helper.utils import name_from_tags
from aws_ml_helper.snapshot import get_snapshot
from aws_ml_helper.volume import volume_attach, get_volume, volume_create


def start_spot_instance(config, name, bid_price, ami_id=None,
                        instance_type=None, snapshot_name=None,
                        mount_point=None):
    """Starts a spot instance.

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Spot instance name
        bid_price (int): Bidding price for the instance
        ami_id (str): AMI id to use. If not provided, value form the
            configuration will be used
        instance_type (str): Instance type to use. If not provided, value from
            the configuration will be used.
        snapshot_name (str): Name of the snapshot from which the attached
            volume will be created
        mount_point (str): Path where the volume should be mounted
    """
    ec2 = boto.client('ec2', config)
    response = ec2.request_spot_instances(
        InstanceCount=1,
        Type='one-time',
        LaunchSpecification={
            'ImageId': ami_id or config.ami_id,
            'InstanceType': instance_type or config.instance_type,
            'KeyName': f'access-key-{config.vpc_name}',
            'EbsOptimized': True,
            'Placement': {
                'AvailabilityZone': config.availability_zone,
            },
            # 'BlockDeviceMappings': [
            #     {
            #         'DeviceName': '/dev/sda1',
            #         'Ebs': {
            #             'DeleteOnTermination': False,
            #             'VolumeSize': 128,
            #             'VolumeType': 'gp2'
            #         },
            #     },
            # ],

            'Monitoring': {'Enabled': True},
            'NetworkInterfaces': [
                {
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'Groups': [config.ec2_security_group_id],
                    'SubnetId': config.subnet_id
                },
            ],
        },
        SpotPrice=f'{bid_price}',
        InstanceInterruptionBehavior='terminate'
    )
    click.echo('Spot instance request created.')
    request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
    waiter = ec2.get_waiter('spot_instance_request_fulfilled')
    waiter.wait(SpotInstanceRequestIds=[request_id])
    response = ec2.describe_spot_instance_requests(
        SpotInstanceRequestIds=[request_id]
    )
    instance_id = response['SpotInstanceRequests'][0]['InstanceId']
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    click.echo(f'Spot Instance ID: {instance_id}')
    ec2.create_tags(Resources=[instance_id],
                    Tags=[{'Key': 'Name', 'Value': name}])
    response = ec2.describe_instances(
        InstanceIds=[instance_id],
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    instance_ip = (
        response['Reservations'][0]['Instances'][0]['PublicIpAddress']
    )
    click.echo(f'Spot Instance IP: {instance_ip}')

    mount_point = mount_point or config.mount_point
    if mount_point in ('', None):
        # Mount point is not defined we don't know where to mount the volume
        return

    ec2 = boto.resource('ec2', config)
    # Search for a volume with the same name
    volume = get_volume(config, name)
    if volume is not None:
        click.echo(f'Volume "{name}" found - attaching')
        # Attach the volume
        volume_attach(config, name, name, device='xvdh')
        run(config, name, f'sudo mount /dev/xvdh {mount_point}')
    else:
        if snapshot_name is not None:
            snapshot = get_snapshot(config, snapshot_name)
        elif config.snapshot_id not in ('', None):
            snapshot = ec2.Snapshot(config.snapshot_id)
            snapshot_name = name_from_tags(snapshot.tags)
        else:
            # Snapshot not found return
            return
        click.echo(f'Creating volume "{name}" from snapshot "{snapshot_name}"')
        volume_create(config, name, size=snapshot.volume_size,
                      snapshot_name=snapshot_name, wait=True)
        click.echo(f'Attaching volume "{name}"')
        volume_attach(config, name, name, device='xvdh')
        run(config, name, f'sudo mount /dev/xvdh {mount_point}')


def median(l):
    """Calculate median value of the list

    Args:
        l (list of float): List of numbers
    """
    length = len(l)
    sorted_l = sorted(l)
    index = (length - 1) // 2

    if length % 2 == 0:
        return (sorted_l[index] + sorted_l[index + 1]) / 2.0
    else:
        return sorted_l[index]


def spot_price(config, days=7, instance_type=None, value='all'):
    """Show information about spot instance prices in the last n days

    Args:
        config (aws_ml_helper.config.Config): Configuration
        days (int): Show information for the last n days
        instance_type (str): Select instance type. If not provided function
            will use the value in the configuration.
        value (str): Pick which value to show. Default all.
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    ec2 = boto.client('ec2', config)

    r = ec2.describe_spot_price_history(
        StartTime=start_time,
        EndTime=end_time,
        InstanceTypes=[instance_type or config.instance_type],
    )

    prices = [float(p['SpotPrice']) for p in r['SpotPriceHistory']]

    if value == 'all':
        print(tabulate([
            ['Min', min(prices)],
            ['Max', max(prices)],
            ['Mean', sum(prices) / len(prices)],
            ['Median', median(prices)]
        ], tablefmt='fancy_grid', floatfmt='.3f'))
    elif value == 'min':
        print(min(prices))
    elif value == 'max':
        print(max(prices))
    elif value == 'mean':
        print(sum(prices) / len(prices))
    elif value == 'median':
        print(median(prices))
