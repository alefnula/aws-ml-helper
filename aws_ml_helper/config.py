__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '20 October 2010'
__copyright__ = 'Copyright (c) 2010 Viktor Kerkez'

import io
import os
import click
from configparser import ConfigParser


class ConfigError(Exception):
    pass


class Config(object):
    KEYS = [
        'aws_access_key_id', 'aws_secret_access_key', 'region',
        'availability_zone', 'vpc_name', 'vpc_id', 'subnet_id',
        'ec2_security_group_id', 'efs_security_group_id', 'access_key',
        'efs_id', 'ami_id', 'ami_username', 'instance_type'
    ]

    def __init__(self, config, profile):
        """
        Args:
            config (str): Path to the configuration ini file
            profile (str): Profile to use
        """
        self.config = config
        self.profile = profile

        if not os.path.isfile(config):
            data = {}
        else:
            cp = ConfigParser()
            cp.read(config)
            data = cp[profile]

        self.aws_access_key_id = data.get('aws_access_key_id', '')
        self.aws_secret_access_key = data.get('aws_secret_access_key', '')
        self.region = data.get('region', '')
        self.availability_zone = data.get('availability_zone', '')
        self.vpc_name = data.get('vpc_name', '')
        self.vpc_id = data.get('vpc_id', '')
        self.subnet_id = data.get('subnet_id', '')
        self.ec2_security_group_id = data.get('ec2_security_group_id', '')
        self.efs_security_group_id = data.get('efs_security_group_id', '')
        self.access_key = data.get('access_key', '')
        self.efs_id = data.get('efs_id', '')
        self.ami_id = data.get('ami_id', '')
        self.ami_username = data.get('ami_username')
        self.instance_type = data.get('instance_type', '')

    def __str__(self):
        return f'Config({self.config}, {self.profile})'

    __repr__ = __str__

    def configure(self):
        self.aws_access_key_id = click.prompt('AWS Access Key ID')
        self.aws_secret_access_key = click.prompt('AWS Secret Access Key')
        self.region = click.prompt('Select Region Name')
        self.availability_zone = click.prompt('Select Availability Zone')
        self.ami_id = click.prompt('Select default AMI Image ID')
        self.ami_username = click.prompt('AMI username')
        self.instance_type = click.prompt('Select Default Instance Type')

    def get(self, key):
        if key not in self.KEYS:
            raise ConfigError(f'Unknown key "{key}"')
        return getattr(self, key)

    def set(self, key, value):
        if key not in self.KEYS:
            raise ConfigError(f'Unknown key "{key}"')
        setattr(self, key, value)

    def save(self):
        cp = ConfigParser()
        if os.path.isfile(self.config):
            cp.read(self.config)
        if self.profile not in cp.sections():
            cp.add_section(self.profile)
        cp[self.profile]['aws_access_key_id'] = self.aws_access_key_id
        cp[self.profile]['aws_secret_access_key'] = self.aws_secret_access_key
        cp[self.profile]['region'] = self.region
        cp[self.profile]['availability_zone'] = self.availability_zone
        cp[self.profile]['vpc_name'] = self.vpc_name
        cp[self.profile]['vpc_id'] = self.vpc_id
        cp[self.profile]['subnet_id'] = self.subnet_id
        cp[self.profile]['ec2_security_group_id'] = self.ec2_security_group_id
        cp[self.profile]['efs_security_group_id'] = self.efs_security_group_id
        cp[self.profile]['access_key'] = self.access_key
        cp[self.profile]['efs_id'] = self.efs_id
        cp[self.profile]['ami_id'] = self.ami_id
        cp[self.profile]['ami_username'] = self.ami_username
        cp[self.profile]['instance_type'] = self.instance_type
        if not os.path.isdir(os.path.dirname(self.config)):
            os.makedirs(os.path.dirname(self.config))
        with io.open(self.config, 'w') as f:
            cp.write(f)
