from aiohttp_session import get_session
import argparse
import configparser
import os
import sys


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


def remove_special_data(items):
    dico = dict(items)
    del dico["csrf_token"]
    del dico["submit"]
    return dico


async def generate_csrf_meta(request):
    return {
        "csrf_context": await get_session(request),
        "csrf_secret": request.app["config"]["application"]["csrf_secret_key"].encode("ascii")
    }
