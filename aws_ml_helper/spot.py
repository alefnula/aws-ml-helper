__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '20 October 2010'
__copyright__ = 'Copyright (c) 2010 Viktor Kerkez'

from aws_ml_helper import boto
from datetime import datetime, timedelta


def start_spot_instance(config, name, bid_price):
    """Starts a spot instance.

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Spot instance name
        bid_price (int): Bidding price for the instance
    """
    ec2 = boto.client('ec2', config)
    response = ec2.request_spot_instances(
        InstanceCount=1,
        Type='one-time',
        LaunchSpecification={
            'ImageId': config.ami_id,
            'InstanceType': config.instance_type,
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
    request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
    waiter = ec2.get_waiter('spot_instance_request_fulfilled')
    waiter.wait(SpotInstanceRequestIds=[request_id])
    response = ec2.describe_spot_instance_requests(
        SpotInstanceRequestIds=[request_id]
    )
    instance_id = response['SpotInstanceRequests'][0]['InstanceId']
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    print(f'Spot Instance ID: {instance_id}')
    ec2.create_tags(Resources=[instance_id],
                    Tags=[{'Key': 'Name', 'Value': name}])
    response = ec2.describe_instances(
        InstanceIds=[instance_id],
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    instance_ip = (
        response['Reservations'][0]['Instances'][0]['PublicIpAddress']
    )
    print(f'Spot Instance IP: {instance_ip}')


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


def spot_price(config, days=7):
    """Show information about spot instance prices in the last n days

    Args:
        config (aws_ml_helper.config.Config): Configuration
        days (int): Show information for the last n days
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    ec2 = boto.client('ec2', config)

    r = ec2.describe_spot_price_history(
        StartTime=start_time,
        EndTime=end_time,
        InstanceTypes=[config.instance_type],
    )

    prices = [float(p['SpotPrice']) for p in r['SpotPriceHistory']]

    print('Spot Price')
    print(f'    Min:    ${min(prices)}')
    print(f'    Max:    ${max(prices)}')
    print(f'    Mean:   ${sum(prices) / len(prices)}')
    print(f'    Median: ${median(prices)}')
