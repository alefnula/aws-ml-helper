__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '16 March 2018'
__copyright__ = 'Copyright (c)  2018 Viktor Kerkez'

import time
import click
from aws_ml_helper import boto
from aws_ml_helper.table import table
from aws_ml_helper.instance import get_instnace


def images(config):
    """List instances and their state

    Args:
        config (aws_ml_helper.config.Config): Configuration
    """
    ec2 = boto.resource('ec2', config)
    data = []
    for i in ec2.images.filter(Owners=[config.account]):
        data.append([
            i.name,
            i.id,
            i.state,
        ])

    print(table(data, ['name', 'id', 'state']))


def image_create(config, instance_name, image_name, wait):
    """Create an AMI image from an instance

    Args:
        config (aws_ml_helper.config.Config): Configuration
        instance_name (str): Name of the instance from which the image should
            be created.
        image_name (str): Name of the newly created image.
        wait (bool): Should we wait for image to become available
    """
    instance = get_instnace(config, instance_name)
    image = instance.create_image(Name=image_name)
    click.echo(f'Image ID: {image.id}')
    if wait:
        while image.state != 'available':
            time.sleep(0.5)
            image.reload()
