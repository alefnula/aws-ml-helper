Setup
=====

Install `aws-ml-helper`, configure it and create a VPC::

    $ pip install aws-ml-helper
    $ aml config
    $ aml setup-vpc

Now you can use all the commands::

    $ aml --help
    Usage: aml [OPTIONS] COMMAND [ARGS]...

    Options:
      --config PATH   Path to the alternative configuration file.
      --profile TEXT  Configuration file profile.
      --help          Show this message and exit.

    Commands:
      config       Configure AWS ML Helper.
      config-get   Get config value.
      config-list  List all configuration values.
      config-set   Set config value.
      instances    List all instances and their states.
      login        Login to instance.
      run          Run command on a selected instance.
      setup-vpc    Setup VPC on Amazon AWS.
      shell        Run IPython shell with loaded configuration.
      spot-price   Show information about spot instance prices.
      spot-run     Starts a spot instance.
      terminate    Terminate instance.

