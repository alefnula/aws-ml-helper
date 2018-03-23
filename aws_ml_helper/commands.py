__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '20 October 2010'
__copyright__ = 'Copyright (c) 2010 Viktor Kerkez'

import os
import click
import webbrowser
from aws_ml_helper.config import Config, ConfigError, DEFAULT_CONFIG_PATH


@click.group()
@click.option('--config', type=click.Path(exists=True), envvar='AML_CONFIG',
              help='Path to the alternative configuration file.')
@click.option('--profile', default='default', envvar='AML_PROFILE',
              help='Configuration file profile.')
@click.pass_context
def cli(ctx, config, profile):
    if config is None:
        config = os.path.expanduser(DEFAULT_CONFIG_PATH)
        if not os.path.isfile(config) and ctx.invoked_subcommand != 'config':
            click.echo('aml not configured.')
            click.echo('Before usage run: aml config')
            ctx.exit()
    ctx.obj = {
        'config': Config(config, profile)
    }


# VPC Commands

@cli.command('setup-vpc')
@click.option('--name', required=True, help='VPC name')
@click.option(
    '--network-range', default='10.0.0.0/16',
    help='Subnet network range in CIDR notation'
)
@click.option(
    '--allowed-ip', default='0.0.0.0/32',
    help='Address allowed to connect to VPC in CIDR notation'
)
@click.option(
    '--key-dir', type=click.Path(resolve_path=True),
    help='Path to the directory where the access key should be saved'
)
@click.pass_context
def setup_vpc(ctx, name, network_range, allowed_ip, key_dir):
    """Setup VPC on Amazon AWS."""
    from aws_ml_helper.vpc import create_vpc, create_efs, generate_key_pair
    config = ctx.obj['config']
    create_vpc(config, name, network_range, allowed_ip,
               config.availability_zone)
    generate_key_pair(config, key_dir)
    create_efs(config)


# Spot instance

@cli.command('spot-start')
@click.argument('name', required=True)
@click.option('--price', type=float, required=True,
              help='Bidding price for the instance')
@click.option('--ami',
              help='AMI id. If not provided use from configuration')
@click.option('--instance-type',
              help='Instance type. If not provided use from configuration.')
@click.option('--snapshot',
              help='Name of the snapshot from which the attached volume will '
                   'be created')
@click.option('--mount-point', help='Where the volume should be mounted')
@click.pass_context
def spot_start(ctx, name, price, ami, instance_type, snapshot, mount_point):
    """Starts a spot instance."""
    from aws_ml_helper.spot import start_spot_instance
    start_spot_instance(ctx.obj['config'], name, price, ami, instance_type,
                        snapshot, mount_point)


@cli.command('spot-price')
@click.option('--days', type=int, default=7,
              help='Show information for the last n days. Default: 7')
@click.option('--instance-type',
              help='Choose instance type. Default: from configuration')
@click.option('--value', default='all',
              type=click.Choice(['all', 'min', 'max', 'mean', 'median']),
              help='Pick the value you want to see. Default: all')
@click.pass_context
def spot_price(ctx, days=7, instance_type=None, value='all'):
    """Show information about spot instance prices."""
    from aws_ml_helper.spot import spot_price
    spot_price(ctx.obj['config'], days, instance_type, value)


# Instance commands

@cli.command()
@click.pass_context
def instances(ctx):
    """Lists instances."""
    from aws_ml_helper.instance import instances
    instances(ctx.obj['config'])


@cli.command()
@click.argument('name', required=True)
@click.option('--ami',
              help='AMI id. If not provided use from configuration')
@click.option('--instance-type',
              help='Instance type. If not provided use from configuration.')
@click.option('--ebs-size', type=int, default=128,
              help='Size of the EBS Volume in GB')
@click.pass_context
def start(ctx, name, ami, instance_type, ebs_size):
    """Starts an instance."""
    from aws_ml_helper.instance import start
    start(ctx.obj['config'], name, ami, instance_type, ebs_size)


@cli.command()
@click.argument('name', required=True)
@click.pass_context
def stop(ctx, name):
    """Stops an instance."""
    from aws_ml_helper.instance import stop
    stop(ctx.obj['config'], name)


@cli.command()
@click.argument('name', required=True)
@click.pass_context
def terminate(ctx, name):
    """Terminate an instance."""
    from aws_ml_helper.instance import terminate
    terminate(ctx.obj['config'], name)


@cli.command()
@click.argument('name', required=True)
@click.pass_context
def login(ctx, name):
    """Login to instance."""
    from aws_ml_helper.instance import login
    login(ctx.obj['config'], name)


@cli.command()
@click.argument('name', required=True)
@click.argument('command', required=True)
@click.pass_context
def run(ctx, name, command):
    """Runs a command on a selected instance."""
    from aws_ml_helper.instance import run
    run(ctx.obj['config'], name, command)


@cli.command()
@click.argument('source', required=True)
@click.argument('destination', required=True)
@click.pass_context
def cp(ctx, source, destination):
    """Copy file to instance or from instance.

    To copy a file to instance use the following command::

        aml cp /path/to/local/file {instance_name}:/remote/path

    And to copy from an instance use::
        aml cp {instance_name}:/remote/path /local/path
    """
    from aws_ml_helper.instance import cp
    cp(ctx.obj['config'], source, destination)


@cli.command()
@click.argument('remote', required=True)
@click.argument('local', required=True, type=click.Path(resolve_path=True))
@click.pass_context
def mount(ctx, remote, local):
    """Mount a remote folder using sshfs.

    `remote` is a remote path in format {instance}:{remote_path} and `local` is
    a path to the local folder.

    Usage::

        aml mount {instance}:/remote/path /local/path
    """
    from aws_ml_helper.instance import mount
    mount(ctx.obj['config'], remote, local)


@cli.command()
@click.argument('local', required=True,
                type=click.Path(exists=True, dir_okay=True, resolve_path=True))
@click.option('--delete', is_flag=True, default=False,
              help='Delete folder after unmounting')
def umount(local, delete):
    """Unmount a local folder"""
    from aws_ml_helper.instance import umount
    umount(local, delete)


# Image commands

@cli.command()
@click.pass_context
def images(ctx):
    """List AMI images."""
    from aws_ml_helper.image import images
    images(ctx.obj['config'])


@cli.command('image-create')
@click.argument('instance-name', required=True)
@click.argument('image-name', required=True)
@click.option('--wait', is_flag=True, help='Wait for AMI to become available')
@click.pass_context
def image_create(ctx, instance_name, image_name, wait):
    """"Create an image from an instance."""
    from aws_ml_helper.image import image_create
    image_create(ctx.obj['config'], instance_name, image_name, wait)


@cli.command('image-delete')
@click.argument('image-name', required=True)
@click.pass_context
def image_delete(ctx, image_name):
    """Deletes an AMI image."""
    from aws_ml_helper.image import image_delete
    image_delete(config, image_name)


# Volume commands

@cli.command()
@click.pass_context
def volumes(ctx):
    """List all volumes"""
    from aws_ml_helper.volume import volumes
    volumes(ctx.obj['config'])


@cli.command('volume-create')
@click.argument('volume-name', required=True)
@click.option('--size', type=int, default=256, help='Size of the volume in GB')
@click.option('--snapshot-name',
              help='Name of the snapshot from which the volume should be '
                   'created')
@click.option('--wait', is_flag=True, default=False,
              help='Wait for the volume to become available')
@click.pass_context
def volume_create(ctx, volume_name, size, snapshot_name, wait):
    """Create a volume"""
    from aws_ml_helper.volume import volume_create
    volume_create(ctx.obj['config'], volume_name, size, snapshot_name, wait)


@cli.command('volume-attach')
@click.argument('volume-name', required=True)
@click.argument('instance-name', required=True)
@click.option('--device', default='xvdh', help='The device name')
@click.pass_context
def volume_attach(ctx, volume_name, instance_name, device):
    """Attach a volume to instance."""
    from aws_ml_helper.volume import volume_attach
    volume_attach(ctx.obj['config'], volume_name, instance_name, device)


@cli.command('volume-detach')
@click.argument('volume-name', required=True)
@click.argument('instance-name', required=True)
@click.option('--device', default='xvdh', help='The device name')
@click.pass_context
def volume_detach(ctx, volume_name, instance_name, device):
    """Detach a volume from an instance."""
    from aws_ml_helper.volume import volume_detach
    volume_detach(ctx.obj['config'], volume_name, instance_name, device)


@cli.command('volume-delete')
@click.argument('volume-name', required=True)
@click.pass_context
def volume_delete(ctx, volume_name):
    """Delete a volume."""
    from aws_ml_helper.volume import volume_delete
    volume_delete(ctx.obj['config'], volume_name)


# Snapshot commands

@cli.command()
@click.pass_context
def snapshots(ctx):
    """List all snapshots"""
    from aws_ml_helper.snapshot import snapshots
    snapshots(ctx.obj['config'])


@cli.command('snapshot-create')
@click.argument('volume-name', required=True)
@click.argument('snapshot-name', required=True)
@click.option('--default', is_flag=True, default=False,
              help='Is this a default snapshot that should be saved in config')
@click.option('--wait', is_flag=True, default=False,
              help='Wait for snapshot creation to complete')
@click.pass_context
def snapshot_create(ctx, volume_name, snapshot_name, default, wait):
    """Create a snapshot from a volume."""
    from aws_ml_helper.snapshot import snapshot_create
    snapshot_create(
        ctx.obj['config'], volume_name, snapshot_name, default, wait
    )


# Configuration commands

@cli.command()
@click.pass_context
def config(ctx):
    """Configure AWS ML Helper.

    Configuration of aml will ask you to enter following values:

    \b
        $ aml config
        AWS Account ID: 503........7
        AWS Access Key ID: AKI................C
        AWS Secret Access Key: Jgd....................................Y
        Select Region Name: us-east-1
        Select Availability Zone: us-east-1a
        Select default AMI Image ID: ami-b......4
        AMI Username: ubuntu
        Select Default Instance Type: p3.2xlarge

    You can get or set configuration keys using:

    \b
        $ aml config-list
        $ aml config-get region
        $ aml config-set region us-east-2
    """
    c = ctx.obj['config']
    c.configure()
    c.save()


@cli.command('config-list')
@click.pass_context
def config_list(ctx):
    """List all configuration values."""
    c = ctx.obj['config']
    for key in c.KEYS:
        click.secho(f'{key}: ', nl=False, fg='green')
        click.secho(c.get(key), fg='red')


@cli.command('config-get')
@click.argument('key')
@click.pass_context
def config_get(ctx, key):
    """Get config value."""
    c = ctx.obj['config']
    try:
        click.secho(f'{key}: ', nl=False, fg='green')
        click.secho(c.get(key), fg='red')
    except ConfigError as e:
        click.secho(str(e), fg='red')


@cli.command('config-set')
@click.argument('key')
@click.argument('value')
@click.pass_context
def config_set(ctx, key, value):
    """Set config value."""
    c = ctx.obj['config']
    try:
        c.set(key, value)
        c.save()
        click.secho(f'{key}: ', nl=False, fg='green')
        click.secho(c.get(key), fg='red')
    except ConfigError as e:
        click.secho(str(e), fg='red')


# Shell & Console

@cli.command()
@click.pass_context
def shell(ctx):
    """Run IPython shell with loaded configuration."""
    try:
        from IPython import embed
        from aws_ml_helper import boto

        user_ns = {
            'config': ctx.obj['config'],
            'boto': boto
        }
        embed(user_ns=user_ns)
    except ImportError:
        click.secho('IPython is not installed', fg='red')


@cli.command()
@click.pass_context
def console(ctx):
    """Open amazon web console."""
    account = ctx.obj['config'].account
    webbrowser.open_new_tab(f'https://{account}.signin.aws.amazon.com/console')
