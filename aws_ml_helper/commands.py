__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '20 October 2010'
__copyright__ = 'Copyright (c) 2010 Viktor Kerkez'

import os
import click
from aws_ml_helper.config import Config, ConfigError


@click.group()
@click.option('--config', type=click.Path(exists=True),
              help='Path to the alternative configuration file.')
@click.option('--profile', default='default',
              help='Configuration file profile.')
@click.pass_context
def cli(ctx, config, profile):
    if config is None:
        config = os.path.expanduser('~/.aws-ml-helper/config.ini')
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

@cli.command('spot-run')
@click.option('--name', required=True, help='Instance name')
@click.option('--price', type=float, required=True,
              help='Bidding price for the instance')
@click.pass_context
def spot_run(ctx, name, price):
    """Starts a spot instance."""
    from aws_ml_helper.spot import start_spot_instance
    start_spot_instance(ctx.obj['config'], name, price)


@cli.command('spot-price')
@click.option('--days', type=int, default=7,
              help='Show information for the last n days')
@click.pass_context
def spot_price(ctx, days=7):
    """Show information about spot instance prices."""
    from aws_ml_helper.spot import spot_price
    spot_price(ctx.obj['config'], days)


# Instance commands

@cli.command()
@click.pass_context
def instances(ctx):
    """List all instances and their states."""
    from aws_ml_helper.instance import instances
    instances(ctx.obj['config'])


@cli.command()
@click.argument('name', required=True)
@click.pass_context
def terminate(ctx, name):
    """Terminate instance."""
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
    """Run command on a selected instance."""
    from aws_ml_helper.instance import run
    run(ctx.obj['config'], name, command)


# Configuration commands

@cli.command()
@click.pass_context
def config(ctx):
    """Configure AWS ML Helper.

    Configuration of aml will ask you to enter following values:

    \b
        $ aml config
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


# Shell

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
