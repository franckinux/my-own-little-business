import binascii
import os
import sys

from cryptography import fernet
from utils import read_configuration_file
from utils import write_configuration_file


def get_random_string(length):
     return binascii.b2a_hex(os.urandom(length)).decode("ascii")


if __name__ == "__main__":
    config = read_configuration_file()
    if not config:
        sys.exit(1)

    fernet_key = fernet.Fernet.generate_key()
    config["application"]["session_secret_key"] = fernet_key.decode("ascii")
    config["application"]["secret_key"] = get_random_string(16)

    write_configuration_file(config)
