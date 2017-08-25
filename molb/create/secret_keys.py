#!/usr/bin/python3
import sys

from cryptography import fernet
from passlib.pwd import genword
from molb.utils import read_configuration_file
from molb.utils import write_configuration_file


if __name__ == "__main__":
    config = read_configuration_file()
    if not config:
        sys.exit(1)

    fernet_key = fernet.Fernet.generate_key()
    config["application"]["session_secret_key"] = fernet_key.decode("ascii")
    config["application"]["secret_key"] = genword(length=32, charset="ascii_50")

    write_configuration_file(config)
