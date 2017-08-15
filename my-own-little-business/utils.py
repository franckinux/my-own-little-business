# import argparse
import configparser
import os
import sys


def read_configuration_file():
    directory = os.path.dirname(os.path.abspath(__file__))
    default_config_file = os.path.join(directory, "config", "my-own-little-business.ini"),

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
