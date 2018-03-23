__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '20 October 2010'
__copyright__ = 'Copyright (c) 2010 Viktor Kerkez'

import os
import click
import paramiko
from tabulate import tabulate
from aws_ml_helper import boto
from aws_ml_helper.utils import name_from_tags


def instances(config):
    """List instances and their state

    Args:
        config (aws_ml_helper.config.Config): Configuration
    """
    ec2 = boto.resource('ec2', config)
    data = []
    for i in ec2.instances.all():
        data.append([
            name_from_tags(i.tags),
            i.id,
            i.state['Name'],
            i.public_ip_address or 'no ip'
        ])

    print(tabulate(
        data, ['name', 'id', 'state', 'public ip'], config.table_format
    ))


def get_instance(config, name):
    """Returns an instance object with selected name or returns `None` if the
    instance is not found.

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Instance name

    Returns:
        Instance if found or None
    """
    ec2 = boto.resource('ec2', config)
    instance_list = list(ec2.instances.filter(
        Filters=[{'Name': 'tag:Name', 'Values': [name]}]
    ))
    if len(instance_list) == 0:
        click.secho(f'Instance "{name}" not found')
        return None
    elif len(instance_list) > 1:
        click.secho(f'Multiple instances with name "{name}" found.')
        return None
    return instance_list[0]


def start(config, name, ami_id, instance_type, ebs_size=128):
    """Start an instance.

    If an instance with this name already exists and it's stopped, it will just
    start the instance. If the instance does not exist, it will start it.


    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Instance name
        ami_id (str): AMI id to use. If not provided, value form the
            configuration will be used
        instance_type (str): Instance type to use. If not provided, value from
            the configuration will be used.
        ebs_size (int): Size of the EBS Volume in GB
    """
    ec2 = boto.resource('ec2', config)
    instance = get_instance(config, name)

    if instance is None:
        # Create an instance
        instance_list = ec2.create_instances(
            ImageId=ami_id or config.ami_id,
            InstanceType=instance_type or config.instance_type,
            KeyName=f'access-key-{config.vpc_name}',
            MinCount=1,
            MaxCount=1,
            BlockDeviceMappings=[
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'DeleteOnTermination': True,
                        'VolumeSize': ebs_size,
                        'VolumeType': 'gp2'
                    },
                },
            ],
            Monitoring={'Enabled': True},
            Placement={
                'AvailabilityZone': config.availability_zone,
            },
            InstanceInitiatedShutdownBehavior='stop',
            NetworkInterfaces=[
                {
                    'DeviceIndex': 0,
                    'AssociatePublicIpAddress': True,
                    'Groups': [config.ec2_security_group_id],
                    'SubnetId': config.subnet_id
                },
            ],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': name}]
                },
            ],
        )
        instance = instance_list[0]
    else:
        # Start an instance
        instance.start()
    # Wait for the instance
    instance.wait_until_running()
    print(f'Instance ID: {instance.id}')


def stop(config, name):
    """Stop instance

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Name of the instance
    """
    instance = get_instance(config, name)
    if instance is not None:
        instance.stop()


def terminate(config, name):
    """Terminate instance

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Name of the instance
    """
    instance = get_instance(config, name)
    if instance is not None:
        instance.terminate()


def login(config, name):
    """Login to instance.

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Name of the instance to log in
    """
    instance = get_instance(config, name)
    if instance is not None:
        os.system(
            f'ssh -o "StrictHostKeyChecking no" -i "{config.access_key}" '
            f'"{config.ami_username}@{instance.public_ip_address}"'
        )


def run(config, name, command, silent=False):
    """Run command on the selected instance

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Name of the instance
        command (str): Command to run
        silent (bool): Should it print out the results or not
    """
    instance = get_instance(config, name)
    if instance is not None:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(instance.public_ip_address,
                    username=config.ami_username,
                    key_filename=config.access_key)
        stdin, stdout, stderr = ssh.exec_command(command)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        if not silent:
            if out.strip() != '':
                click.echo(out)
            if err.strip() != '':
                click.secho(err, fg='red')
        return out, err


def cp(config, source, destination):
    """Copy file to instance or from instance.

    To copy a file to instance use the following command::

        aml cp /path/to/local/file {instance_name}:/remote/path

    And to copy from an instance use::

        aml cp {instance_name}:/remote/path /local/path

    Args:
        config (aws_ml_helper.config.Config): Configuration
        source (str): Source file
        destination (src): Destination file
    """
    if ':' in source or ':' in destination:
        if ':' in source:
            instance_name, source = source.split(':')
            from_instance = True
        else:
            instance_name, destination = destination.split(':')
            from_instance = False

        instance = get_instance(config, instance_name)
        if instance is not None:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_ip_address,
                        username=config.ami_username,
                        key_filename=config.access_key)
            sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
            if from_instance:
                sftp.get(source, destination)
            else:
                sftp.put(source, destination)
    else:
        click.secho('Both paths are local paths.', fg='red')


def mount(config, remote, local):
    """Mount a remote folder using sshfs

    Usage::

        aml mount {instance}:/remote/path /local/path

    Args:
        config (aws_ml_helper.config.Config): Configuration
        remote (str): Remote path in format `{instance}:{path}`
        local (str): Local path
    """
    if os.system('which sshfs >> /dev/null') != 0:
        click.secho('sshfs must be installed.', fg='red')
    if not os.path.isdir(local):
        os.makedirs(local)

    instance_name, _, path = remote.partition(':')
    instance = get_instance(config, instance_name)
    os.system(
        f'sshfs "{config.ami_username}@{instance.public_ip_address}:{path}" '
        f'"{local}" -o IdentityFile="{config.access_key}"'
    )


def umount(local, delete=False):
    """Unmount a local folder

    Args:
        local (str): Path to the local folder.
        delete (bool): Delete local folder after unmount
    """
    os.system(f'umount {local}')
    if delete:
        os.rmdir(local)
