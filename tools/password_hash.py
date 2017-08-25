#!/usr/bin/python3
import sys

from passlib.hash import sha256_crypt


password = sys.argv[1]
password_hash = sha256_crypt.hash(password)
print("password = " + password)
print("password hash = " + password_hash)
