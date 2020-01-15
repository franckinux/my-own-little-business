import configparser
import os
import sys


def read_configuration_file():
    config = configparser.ConfigParser()
    try:
        conf_filename = os.environ.get("MOLB_CONFIG")
        config.read(conf_filename)
    except Exception:
        sys.stderr.write(
            "problem encountered while reading the configuration file %s\n" %
            conf_filename
        )
        return None
    return config


def write_configuration_file(config):
    conf_filename = os.environ.get("MOLB_CONFIG")

    with open(conf_filename, "w") as f:
        config.write(f)
