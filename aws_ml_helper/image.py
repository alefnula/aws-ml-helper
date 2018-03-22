__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '16 March 2018'
__copyright__ = 'Copyright (c)  2018 Viktor Kerkez'

import time
import click
from tabulate import tabulate
from aws_ml_helper import boto
from aws_ml_helper.instance import get_instance


def get_image(config, name):
    """Returns an image object with selected name or returns `None` if the
        image is not found.

        Args:
            config (aws_ml_helper.config.Config): Configuration
            name (str): Volume name

        Returns:
            Volume if found or None
        """
    ec2 = boto.resource('ec2', config)
    image_list = ec2.images.filter(
        Owners=[config.account],
        Filters=[{'Name': 'Name', 'Values': [name]}]
    )
    if len(image_list) == 0:
        click.secho(f'Volume "{name}" not found')
        return None
    elif len(image_list) > 1:
        click.secho(f'Multiple volumes with name "{name}" found.')
        return None
    return image_list[0]


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

    print(tabulate(data, ['name', 'id', 'state'], 'fancy_grid'))


def image_create(config, instance_name, image_name, wait):
    """Create an AMI image from an instance

    Args:
        config (aws_ml_helper.config.Config): Configuration
        instance_name (str): Name of the instance from which the image should
            be created.
        image_name (str): Name of the newly created image.
        wait (bool): Should we wait for image to become available
    """
    instance = get_instance(config, instance_name)
    image = instance.create_image(Name=image_name)
    click.echo(f'Image ID: {image.id}')
    if wait:
        while image.state != 'available':
            time.sleep(0.5)
            image.reload()


def image_delete(config, image_name):
    """Deletes an image.

    Args:
        config (aws_ml_helper.config.Config): Configuration
        image_name (str): Image name
    """
    image = get_image(config, image_name)
    if image:
        image.deregister()
