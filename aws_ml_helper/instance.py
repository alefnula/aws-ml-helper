__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '20 October 2010'
__copyright__ = 'Copyright (c) 2010 Viktor Kerkez'

import os
import click
import paramiko
from aws_ml_helper import boto


def instances(config):
    """List instances and their state

    Args:
        config (aws_ml_helper.config.Config): Configuration
    """
    ec2 = boto.client('ec2', config)
    response = ec2.describe_instances()
    instances = [i for r in response['Reservations'] for i in r['Instances']]
    for i in instances:
        name = [t['Value'] for t in i['Tags'] if t['Key'] == 'Name'][0]
        print(f'{name:15} [{i["State"]["Name"]}]: {i["PublicIpAddress"]}')


def terminate(config, name):
    """Terminate instance

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Name of the instance
    """
    ec2 = boto.client('ec2', config)
    response = ec2.describe_instances(Filters=[{'Name': 'tag:Name',
                                                'Values': [name]}])
    instance_id = response['Reservations'][0]['Instances'][0]['InstanceId']
    ec2.terminate_instances(InstanceIds=[instance_id])


def login(config, name):
    """Login to instance.

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Name of the instance to log in
    """
    ec2 = boto.client('ec2', config)
    response = ec2.describe_instances(Filters=[{'Name': 'tag:Name',
                                                'Values': [name]}])
    ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
    os.system(f'ssh -i "{config.access_key}" "{config.ami_username}@{ip}"')


def run(config, name, command):
    """Run command on the selected instance

    Args:
        config (aws_ml_helper.config.Config): Configuration
        name (str): Name of the instance
        command (str): Command to run
    """
    ec2 = boto.client('ec2', config)
    response = ec2.describe_instances(Filters=[{'Name': 'tag:Name',
                                                'Values': [name]}])
    ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=config.ami_username,
                key_filename=config.access_key)
    stdin, stdout, stderr = ssh.exec_command(command)
    out = stdout.read().decode('utf-8')
    if out.strip() != '':
        click.echo(out)
    err = stderr.read().decode('utf-8')
    if err.strip() != '':
        click.secho(err, fg='red')
