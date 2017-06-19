import argparse
import configparser
import os


def read_configuration_file():
    directory = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(description="my-own-little-business configuration")
    parser.add_argument("-c", "--config",
                        default=os.path.join(directory, "config", "my-own-little-business.ini"),
                        help="configuration file")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    try:
        config.read(args.config)
    except:
        sys.stderr.write("problem encountered while processing configuration file %s\n" % args.config)
        return None

    return config
