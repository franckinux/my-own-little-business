import asyncio
from datetime import datetime
import os
import sys

import asyncpg
from passlib.hash import sha256_crypt
from passlib.pwd import genword

from utils import read_configuration_file


async def main(config, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    dsn = "postgres://{}:{}@{}:{}/{}".format(
        config["username"], config["password"],
        config["host"], config["port"],
        config["database"]
    )
    conn = await asyncpg.connect(dsn)

    # last invoice date
    await conn.execute(
        ("INSERT INTO storage(last_invoice_date) VALUES ($1)"),
         datetime.today()
    )

    # create a dummy repo for creating the admin
    repo_id = await conn.fetchval(
        "INSERT INTO repository (name, opened) VALUES ($1, $2) RETURNING id",
        "Dummy", False
    )

    # TODO : use the right password generator !
    # admin_password = genword(length=8, charset="ascii_50")
    admin_password = "admin"
    print("Admin password = {}".format(admin_password ))

    # super user
    await conn.execute(
        ("INSERT INTO client (login, password_hash, confirmed, super_user, "
        "first_name, last_name, email_address, phone_number, repository_id) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)"),
            "admin",
            sha256_crypt.hash(admin_password),
            True,
            True,
            "Tom",
            "Sawyer",
            "tom@literature.net",
            "06-88-77-66-55",
            repo_id
    )

if __name__ == "__main__":
    config = read_configuration_file()
    if not config:
        sys.exit(1)
    config = config["database"]
    config["password"] = os.getenv("PG_PASS", "") or config["password"]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(config))
