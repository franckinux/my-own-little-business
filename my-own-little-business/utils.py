# import argparse
import configparser
import os
import sys


def get_config_filename():
    directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(directory, "config", "my-own-little-business.ini")


def read_configuration_file():
    default_config_file = get_config_filename()

    # # when used with Gunicorn, it gets the arguments from the gunicorn command
    # parser = argparse.ArgumentParser(description="my-own-little-business configuration")
    # parser.add_argument("-c", "--config",
    #                     default=default_config_file,
    #                     help="configuration file")
    # args = parser.parse_args()

    config = configparser.ConfigParser()
    try:
        # config.read(args.config)
        config.read(default_config_file)
    except:
        # sys.stderr.write("problem encountered while processing configuration file %s\n" % args.config)
        sys.stderr.write("problem encountered while processing configuration file %s\n" % default_config_file)
        return None

    return config


def write_configuration_file(config):
    default_config_file = get_config_filename()

    with open(default_config_file, "w") as f:
        config.write(f)
