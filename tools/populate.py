#!/usr/bin/python3
import asyncio
from datetime import datetime
import os
import sys

import asyncpg
from passlib.hash import sha256_crypt

from molb.utils import read_configuration_file


async def main(config, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    dsn = "postgres://{}:{}@{}:{}/{}".format(
        config["username"], config["password"],
        config["host"], config["port"],
        config["database"]
    )
    conn = await asyncpg.connect(dsn)

    # create basic objects

    # repo_1
    repo_1_id = await conn.fetchval(
        "INSERT INTO repository (name) VALUES ($1) RETURNING id",
        "Haut village"
    )

    # repo_2
    repo_2_id  = await conn.fetchval(
        "INSERT INTO repository (name) VALUES ($1) RETURNING id",
        "Bas village"
    )

    # client 1
    client_1_id = await conn.fetchval(
        ("INSERT INTO client (login, password_hash, confirmed, super_user, "
        "first_name, last_name, email_address, phone_number, repository_id) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING id"),
            "rabid",
            sha256_crypt.hash("abcdef"),
            True,
            False,
            "Raymonde",
            "Bidochon",
            "franck@barbenoi.re",
            "01-40-50-50-01",
            repo_1_id
    )

    # client 2
    client_2_id = await conn.fetchval(
        ("INSERT INTO client (login, password_hash, confirmed, super_user, "
        "first_name, last_name, email_address, phone_number, repository_id) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING id"),
            "robid",
            sha256_crypt.hash("ABCDEF"),
            True,
            False,
            "Robert",
            "Bidochon",
            "contact@franck-barbenoire.fr",
            "01-40-50-50-02",
            repo_1_id
    )

    # client 3
    client_3_id = await conn.fetchval(
        ("INSERT INTO client (login, password_hash, confirmed, super_user, "
        "first_name, last_name, email_address, phone_number, repository_id) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING id"),
            "kbid",
            sha256_crypt.hash("123456"),
            True,
            False,
            "Kador",
            "Bidochon",
            "fbarbenoire@yahoo.fr",
            "01-40-50-50-03",
            repo_2_id
    )

    # product_1
    product_1_id = await conn.fetchval(
        "INSERT INTO product (name, description, price) VALUES ($1, $2, $3) RETURNING id",
        "Pain au sarrasin", "Pain avec de la faine de sarrasin dedans", 5
    )

    # product_2
    product_2_id = await conn.fetchval(
        "INSERT INTO product (name, description, price) VALUES ($1, $2, $3) RETURNING id",
        "Pain de seigle", "Pain avec de la faine de seigle dedans", 4
    )

    # batch_1
    batch_1_id = await conn.fetchval(
        "INSERT INTO batch (date, capacity, opened) VALUES ($1, $2, $3) RETURNING id",
        datetime(2017, 8, 18, 8, 0, 0), 50, True
    )

    # batch_2
    batch_2_id = await conn.fetchval(
        "INSERT INTO batch (date, capacity, opened) VALUES ($1, $2, $3) RETURNING id",
        datetime(2017, 8, 19, 8, 0, 0), 50, True
    )

    # batch_3
    batch_3_id = await conn.fetchval(
        "INSERT INTO batch (date, capacity, opened) VALUES ($1, $2, $3) RETURNING id",
        datetime(2017, 12, 31, 8, 0, 0), 20, True
    )
    batch_3_id

    # link basic object between them

    # ORDER 1

    # order-1 to client and batch
    order_1_id = await conn.fetchval(
        "INSERT INTO order_ (total, client_id, batch_id, placed_at) VALUES ($1, $2, $3, $4) RETURNING id",
        20, client_1_id, batch_1_id, datetime(2017, 8, 8, 8, 0, 0)
    )

    # order-1 to products
    await conn.execute(
        "INSERT INTO order_product_association (order_id, product_id, quantity) VALUES ($1, $2, $3)",
        order_1_id, product_1_id, 2
    )
    await conn.execute(
        "INSERT INTO order_product_association (order_id, product_id, quantity) VALUES ($1, $2, $3)",
        order_1_id, product_2_id, 3
    )

    # ORDER 2

    # order-2 to client and batch
    order_2_id = await conn.fetchval(
        "INSERT INTO order_ (total, client_id, batch_id, placed_at) VALUES ($1, $2, $3, $4) RETURNING id",
        26, client_1_id, batch_2_id, datetime(2017, 8, 10, 8, 0, 0)
    )

    # order-2 to products
    await conn.execute(
        "INSERT INTO order_product_association (order_id, product_id, quantity) VALUES ($1, $2, $3)",
        order_2_id, product_1_id, 3
    )

    # ORDER 3

    # order-3 to client and batch
    order_3_id = await conn.fetchval(
        "INSERT INTO order_ (total, client_id, batch_id, placed_at) VALUES ($1, $2, $3, $4) RETURNING id",
        30, client_2_id, batch_1_id, datetime(2017, 8, 10, 8, 0, 0)
    )

    # order-3 to products
    await conn.execute(
        "INSERT INTO order_product_association (order_id, product_id, quantity) VALUES ($1, $2, $3)",
        order_3_id, product_1_id, 3
    )

    # ORDER 4

    # order-4 to client and batch
    order_4_id = await conn.fetchval(
        "INSERT INTO order_ (total, client_id, batch_id, placed_at) VALUES ($1, $2, $3, $4) RETURNING id",
        50, client_3_id, batch_1_id, datetime(2017, 8, 10, 8, 0, 0)
    )

    # order-4 to products
    await conn.execute(
        "INSERT INTO order_product_association (order_id, product_id, quantity) VALUES ($1, $2, $3)",
        order_4_id, product_2_id, 7
    )


if __name__ == "__main__":
    config = read_configuration_file()
    if not config:
        sys.exit(1)
    config = config["database"]
    config["password"] = os.getenv("PG_PASS", "") or config["password"]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(config))
