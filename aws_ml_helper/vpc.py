__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '20 October 2010'
__copyright__ = 'Copyright (c) 2010 Viktor Kerkez'

import io
import os
import time
from aws_ml_helper import boto


def create_vpc(config, name, network_range='10.0.0.0/16',
               allowed_ip='0.0.0.0/32', availability_zone='us-east-1a'):
    """Creates a VPC

    Args:
        config (aws_ml_helper.config.Config): Configuration object
        name (str): VPC name
        network_range (str): The IPv4 network range for the VPC, in CIDR
            notation. For example, 10.0.0.0/16
        allowed_ip (str): Public IP address from which the VPC instances will
            be accessible in CIDR notation.
        availability_zone: VPC availability zone
    """

    ec2 = boto.client('ec2', config)

    print('Create VPC')
    response = ec2.create_vpc(CidrBlock=network_range)
    vpc_id = response['Vpc']['VpcId']
    # Sleep for a second because the the object is created asynchronously. It's
    # not created when the response comes back from the server.
    time.sleep(1)
    ec2.create_tags(Resources=[vpc_id],
                    Tags=[{'Key': 'Name', 'Value': name}])
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})

    print('Create the gateway')
    response = ec2.create_internet_gateway()
    # Sleep for a second because the the object is created asynchronously. It's
    # not created when the response comes back from the server.
    time.sleep(1)
    gateway_id = response['InternetGateway']['InternetGatewayId']
    ec2.create_tags(Resources=[gateway_id],
                    Tags=[{'Key': 'Name', 'Value': f'{name}-gateway'}])
    ec2.attach_internet_gateway(VpcId=vpc_id, InternetGatewayId=gateway_id)

    print('Create subnet')
    response = ec2.create_subnet(VpcId=vpc_id, CidrBlock=network_range,
                                 AvailabilityZone=availability_zone)
    # Sleep for a second because the the object is created asynchronously. It's
    # not created when the response comes back from the server.
    time.sleep(1)
    subnet_id = response['Subnet']['SubnetId']
    ec2.create_tags(Resources=[subnet_id],
                    Tags=[{'Key': 'Name', 'Value': f'{name}-subnet'}])

    print('Create routing table')
    response = ec2.create_route_table(VpcId=vpc_id)
    # Sleep for a second because the the object is created asynchronously. It's
    # not created when the response comes back from the server.
    time.sleep(1)
    route_table_id = response['RouteTable']['RouteTableId']
    ec2.create_tags(Resources=[route_table_id],
                    Tags=[{'Key': 'Name', 'Value': f'{name}-route-table'}])
    ec2.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_id)
    ec2.create_route(RouteTableId=route_table_id, GatewayId=gateway_id,
                     DestinationCidrBlock='0.0.0.0/0')

    print('Create security group for instances')
    response = ec2.create_security_group(
        VpcId=vpc_id, GroupName=f'{name}-ec2-security-group',
        Description=f'Security Group for {name} VPC instances'
    )
    # Sleep for a second because the the object is created asynchronously. It's
    # not created when the response comes back from the server.
    time.sleep(1)
    ec2_security_group_id = response['GroupId']
    # Open port for ssh
    ec2.authorize_security_group_ingress(
        GroupId=ec2_security_group_id, IpProtocol='tcp',
        FromPort=22, ToPort=22,
        CidrIp=allowed_ip
    )
    # Open port for tensorboard
    ec2.authorize_security_group_ingress(
        GroupId=ec2_security_group_id, IpProtocol='tcp',
        FromPort=6006, ToPort=6006,
        CidrIp=allowed_ip
    )
    # Open port for jupyter notebook
    ec2.authorize_security_group_ingress(
        GroupId=ec2_security_group_id, IpProtocol='tcp',
        FromPort=8888, ToPort=8888,
        CidrIp=allowed_ip
    )

    print('Create security group for EFS')
    response = ec2.create_security_group(
        VpcId=vpc_id, GroupName=f'{name}-efs-security-group',
        Description=f'Security Group for {name} VPC EFS'
    )
    # Sleep for a second because the the object is created asynchronously. It's
    # not created when the response comes back from the server.
    time.sleep(1)
    efs_security_group_id = response['GroupId']
    ec2.authorize_security_group_ingress(
        GroupId=efs_security_group_id,
        IpPermissions=[
            {
                'FromPort': 2049,
                'IpProtocol': 'tcp',
                'ToPort': 2049,
                'UserIdGroupPairs': [{'GroupId': ec2_security_group_id}]
            },
        ]
    )

    config.vpc_id = vpc_id
    config.vpc_name = name
    config.subnet_id = subnet_id
    config.ec2_security_group_id = ec2_security_group_id
    config.efs_security_group_id = efs_security_group_id
    config.save()

    return {
        'vpc_id': vpc_id,
        'vpc_name': name,
        'subnet': subnet_id,
        'ec2_security_group': ec2_security_group_id,
        'efs_security_group': efs_security_group_id
    }


def generate_key_pair(config, path):
    """Generate key pair and save it to the keys subdirectory

    Args:
        config (aws_ml_helper.config.Config): Configuration
        path (str): Path to the directory where the access key should be saved
    """
    ec2 = boto.client('ec2', config)

    print('Generating key-pair')
    full_name = f'access-key-{config.vpc_name}'
    response = ec2.create_key_pair(KeyName=full_name)
    if not os.path.isdir(path):
        os.makedirs(path)
    key_path = os.path.join(path, f'{full_name}.pem')
    with io.open(key_path, 'w') as f:
        f.write(response['KeyMaterial'])
    os.chmod(key_path, 0o400)
    config.access_key = key_path
    config.save()


def create_efs(config):
    """Create and configure EFS

    Args:
        config (aws_ml_helper.config.Config): Configuration
    """
    efs = boto.client('efs', config)

    print('Creating EFS')
    token = f'{config.vpc_name}-efs'
    response = efs.create_file_system(CreationToken=token)
    efs_id = response['FileSystemId']
    # Sleep for a second because the the object is created asynchronously. It's
    # not created when the response comes back from the server.
    time.sleep(1)
    efs.create_tags(
        FileSystemId=efs_id, Tags=[{'Key': 'Name', 'Value': token}]
    )
    # Wait until it's in the available state
    while True:
        response = efs.describe_file_systems(FileSystemId=efs_id)
        if response['FileSystems'][0]['LifeCycleState'] == 'available':
            break
    efs.create_mount_target(
        FileSystemId=efs_id,
        SubnetId=config.subnet_id,
        SecurityGroups=[config.efs_security_group_id]
    )
    config.efs_id = efs_id
    config.save()
