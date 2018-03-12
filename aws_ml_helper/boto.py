__author__ = 'Viktor Kerkez <alefnula@gmail.com>'
__date__ = '20 October 2010'
__copyright__ = 'Copyright (c) 2010 Viktor Kerkez'

import boto3


def client(service, config):
    """Returns a client for a specific service.

    Args:
        service (str): Service name
        config (aws_ml_helper.config.Config): Configuration
    """
    return boto3.client(service, aws_access_key_id=config.aws_access_key_id,
                        aws_secret_access_key=config.aws_secret_access_key,
                        region_name=config.region)
