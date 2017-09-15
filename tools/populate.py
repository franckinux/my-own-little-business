#!/usr/bin/python3
import asyncio
import datetime
import os
import sys

import asyncpg
from passlib.hash import sha256_crypt

from molb.utils import read_configuration_file


# https://stackoverflow.com/questions/6558535/find-the-date-for-the-first-monday-after-a-given-a-date
def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days=days_ahead)


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

    # repositories
    # ============

    # repo_1
    repo_1_id = await conn.fetchval(
        "INSERT INTO repository (name) VALUES ($1) RETURNING id", "Legrand")

    # repo_2
    repo_2_id = await conn.fetchval(
        "INSERT INTO repository (name) VALUES ($1) RETURNING id", "Madrange")

    # repo_3
    repo_3_id = await conn.fetchval(
        "INSERT INTO repository (name) VALUES ($1) RETURNING id", "Valeo")

    # clients
    # =======

    # client 1
    await conn.fetchval(
        ("INSERT INTO client (login, password_hash, confirmed, super_user, "
        "first_name, last_name, email_address, phone_number, repository_id) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING id"),
        "rabid",
        sha256_crypt.hash("abcdef"),
        True,
        False,
        "Raymonde",
        "Bidochon",
        "rabid@franck-barbenoire.fr",
        "01-40-50-50-01",
        repo_1_id
    )

    # client 2
    await conn.fetchval(
        ("INSERT INTO client (login, password_hash, confirmed, super_user, "
        "first_name, last_name, email_address, phone_number, repository_id) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING id"),
        "robid",
        sha256_crypt.hash("ABCDEF"),
        True,
        False,
        "Robert",
        "Bidochon",
        "robid@franck-barbenoire.fr",
        "01-40-50-50-02",
        repo_1_id
    )

    # client 3
    await conn.fetchval(
        ("INSERT INTO client (login, password_hash, confirmed, super_user, "
        "first_name, last_name, email_address, phone_number, repository_id) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING id"),
        "kbid",
        sha256_crypt.hash("123456"),
        True,
        False,
        "Kador",
        "Bidochon",
        "kbid@franck-barbenoire.fr",
        "01-40-50-50-03",
        repo_2_id
    )

    # client 4
    await conn.fetchval(
        ("INSERT INTO client (login, password_hash, confirmed, super_user, "
        "first_name, last_name, email_address, phone_number, repository_id) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING id"),
        "mariethe",
        sha256_crypt.hash("888888"),
        True,
        False,
        "Marie-Thérèse",
        "Des Batignoles",
        "mariethe@franck-barbenoire.fr",
        "01-40-50-50-03",
        repo_3_id
    )

    # products
    # ========

    # product_1
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Semi-complet 1kg (façonné)", "", 4.5, 1
    )

    # product_1bis
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Semi-complet 1kg (moulé)", "", 4.5, 0.9
    )

    # product_2
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Semi-complet 650g (façonné)", "", 3, 0.7
    )

    # product_3
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Lin-sésame-tournesol 1kg (façonné)", "", 6, 1
    )

    # product_3bis
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Lin-sésame-tournesol 1kg (moulé)", "", 6, 0.9
    )

    # product_4
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Lin-sésame-tournesol 650g (façonné)", "", 4.5, 0.7
    )

    # product_5
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Petit épautre 500g (moulé)", "", 4.8, 0.5
    )

    # product_6
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Raisins-noisettes 1kg (moulé)", "", 8, 0.9
    )

    # product_7
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Raisins-noisettes 500g (moulé)", "", 4, 0.5
    )

    # product_8
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Noix 500g (moulé)", "", 4.5, 0.5
    )

    # product_9
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Figues-noix 500g (moulé)", "", 4.5, 0.5
    )

    # product_10
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Pavot 500g (moulé)", "", 4.5, 0.5
    )

    # product_11
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Chocolat-orange 500g (moulé)", "", 4.5, 0.5
    )

    # product_12
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Seigle 1kg (moulé)", "", 5.4, 0.9
    )

    # product_13
    await conn.fetchval(
        "INSERT INTO product (name, description, price, load) VALUES ($1, $2, $3, $4) RETURNING id",
        "Seigle 500g (moulé)", "", 2.8, 0.5
    )

    # batches
    # =======

    # create 5 batches on next week begining from monday 10:00am
    start_day = datetime.datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    next_day = next_weekday(start_day, 0)
    for _ in range(5):
        await conn.fetchval(
            "INSERT INTO batch (date, capacity, opened) VALUES ($1, $2, $3) RETURNING id",
            next_day, 50, True
        )
        next_day += datetime.timedelta(days=1)


if __name__ == "__main__":
    config = read_configuration_file()
    if not config:
        sys.exit(1)
    config = config["database"]
    config["password"] = os.getenv("PG_PASS", "") or config["password"]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(config))
