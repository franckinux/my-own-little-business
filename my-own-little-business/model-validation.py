import asyncio
from datetime import datetime
import os
import sys

from asyncpgsa import pg
from passlib.hash import sha256_crypt
from sqlalchemy import select
from sqlalchemy.engine.url import URL
from sqlalchemy.sql import insert
from sqlalchemy.sql import join
from sqlalchemy.sql import update
from sqlalchemy.sql.expression import and_

from model import Client
from model import Repository
from model import Batch
from model import Product
from model import Order
from model import OrderProductAssociation
from model import PayedStatusEnum
from model import Payment
from utils import read_configuration_file


async def main(config, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    connection_infos = {
        "drivername": "postgres",
        "host": config["host"],
        "port": config["port"],
        "username": config["username"],
        "password": config["password"],
        "database": config["database"]
    }
    dsn = str(URL(**connection_infos))
    await pg.init(dsn)

    # create basic objects
    async with pg.begin():
        # admin
        row = await pg.fetchrow(
            insert(Client).values(
                login="admin", password_hash=sha256_crypt.hash("admin"),
                confirmed=True,
                super_user=True,
                first_name="Tom", last_name="Sawyer",
                email_address="tom@literature.net",
                phone_number="888-888-888"
            ).returning(Client.__table__.c.id)
        )
        client_1_id = row.id

        # client 1
        row = await pg.fetchrow(
            insert(Client).values(
                login="rabid", password_hash="abc",
                first_name="Raymonde", last_name="Bidochon",
                email_address="ra.bidochon@binet.com",
                phone_number="01-40-50-50-01"
            ).returning(Client.__table__.c.id)
        )
        client_1_id = row.id

        # client 2
        row = await pg.fetchrow(
            insert(Client).values(
                login="robid", password_hash="def",
                first_name="Robert", last_name="Bidochon",
                email_address="ro.bidochon@binet.com",
                phone_number="01-40-50-50-02"
            ).returning(Client.__table__.c.id)
        )
        client_2_id = row.id

        # repo_1
        row = await pg.fetchrow(
            insert(Repository).values(name="Haut village").returning(Repository.__table__.c.id)
        )
        repo_1_id = row.id

        # repo_2
        row = await pg.fetchrow(
            insert(Repository).values(name="Bas village").returning(Repository.__table__.c.id)
        )
        repo_2_id = row.id

        # product_1
        row = await pg.fetchrow(
            insert(Product).values(
                name="Pain au sarrasin",
                description="Pain avec de la faine de sarrasin dedans",
                price=5
            ).returning(Product.__table__.c.id)
        )
        product_1_id = row.id

        # product_2
        row = await pg.fetchrow(
            insert(Product).values(
                name="Pain de seigle",
                description="Pain avec de la faine de seigle dedans",
                price=4
            ).returning(Product.__table__.c.id)
        )
        product_2_id = row.id

        # batch_1
        row = await pg.fetchrow(
           insert(Batch).values(
               date=datetime(2017, 6, 18, 8, 0, 0), capacity=50
            ).returning(Batch.__table__.c.id)
        )
        batch_1_id = row.id

        # batch_2
        row = await pg.fetchrow(
            insert(Batch).values(
                date=datetime(2017, 6, 19, 8, 0, 0), capacity=50, opened=False
            ).returning(Batch.__table__.c.id)
        )
        batch_2_id = row.id

    # link basic object between them
    async with pg.begin():
        # repository to clients
        await pg.execute(update(Client).where(
            Client.__table__.c.id == client_1_id
        ).values(
            repository_id=repo_1_id
        ))
        await pg.execute(update(Client).where(
            Client.__table__.c.id == client_2_id
        ).values(
            repository_id=repo_1_id
        ))

        # order-1 to client and batch
        row = await pg.fetchrow(
            insert(Order).values(
                client_id=client_1_id, batch_id=batch_1_id
            ).returning(Order.__table__.c.id)
        )
        order_1_id = row.id

        # order-1 to products
        await pg.execute(
            insert(OrderProductAssociation).values(
                quantity=2,
                order_id=order_1_id, product_id=product_1_id
            )
        )
        await pg.execute(
            insert(OrderProductAssociation).values(
                quantity=3,
                order_id=order_1_id, product_id=product_2_id
            )
        )

        # test simple queries
        row = await pg.fetchrow(
            join(Order.__table__, Client.__table__).select().where(Client.__table__.c.id == client_1_id)
        )
        print("client.first_name =", row.first_name)

        rows = await pg.fetch(
            join(OrderProductAssociation.__table__, Product.__table__).select().where(OrderProductAssociation.__table__.c.order_id == order_1_id)
        )
        for row in rows:
            print("quantity =", row.quantity)
            print("product =", row.name)

        # order-2 to client and batch
        row = await pg.fetchrow(
            insert(Order).values(
                client_id=client_1_id, batch_id=batch_2_id
            ).returning(Order.__table__.c.id)
        )
        order_2_id = row.id

        # order-2 to products
        await pg.execute(
            insert(OrderProductAssociation).values(
                quantity=3,
                order_id=order_2_id, product_id=product_1_id
            )
        )

        # payment to order_2
        row = await pg.fetchrow(
            insert(Payment).values(
                total=10, payed_at=datetime.now(), mode="payed_by_check"
                # total=10, payed_at=datetime.now(), mode=PayedStatusEnum.payed_by_check
            ).returning(Payment.__table__.c.id)
        )
        payement_2_id = row.id

        await pg.execute(update(Order).where(
            Order.__table__.c.id == order_1_id
        ).values(
            payment_id=payement_2_id
        ))

        # ---
        # order-1 to client and batch
        row = await pg.fetchrow(
            insert(Order).values(
                client_id=client_2_id, batch_id=batch_1_id
            ).returning(Order.__table__.c.id)
        )
        order_3_id = row.id

        # order-3 to products
        await pg.execute(
            insert(OrderProductAssociation).values(
                quantity=3,
                order_id=order_3_id, product_id=product_1_id
            )
        )


    # compute batch load
    load = 0
    rows = await pg.fetch(
        select([Order.__table__.c.id]).where(Order.__table__.c.batch_id == batch_1_id)
    )
    order_ids = [row.id for row in rows]

    rows = await pg.fetch(
        join(OrderProductAssociation.__table__, Product.__table__).select().where(OrderProductAssociation.__table__.c.order_id.in_(order_ids))
    )
    for row in rows:
        load += row.quantity * row.load
    print("batch 1 load :", load)
    # print("batch 1 capacity :", batch_1.capacity)
    print("---")

    # compute order total price
    price = 0
    rows = await pg.fetch(
        join(OrderProductAssociation.__table__, Product.__table__).select().where(OrderProductAssociation.__table__.c.order_id == order_1_id)
    )
    for row in rows:
        price += row.quantity * row.price
    print("order 1 total price :", price)
    print("---")

    # search for all orders from a client
    rows = await pg.fetch(
        select([Order]).where(Order.__table__.c.client_id == client_1_id)
    )

    print("{} orders for client_1".format(len(rows.data)))
    for row in rows:
        print("order datetime :", row.placed_at)
    print("---")

    # search for all non payed orders from a client
    rows = await pg.fetch(
        select([Order]).where(Order.__table__.c.client_id == client_1_id)
    )
    order_ids = [row.id for row in rows]

    rows = await pg.fetch(
        join(Order.__table__, Payment.__table__).select().where(
            and_(
                Order.__table__.c.id.in_(order_ids),
                Payment.__table__.c.mode.in_ != PayedStatusEnum.not_payed
            )
        )
    )

    print("{} non payed orders for client_1".format(len(rows.data)))
    for row in rows:
        print("order datetime :", row.placed_at)


if __name__ == "__main__":
    config = read_configuration_file()
    if not config:
        sys.exit(1)
    config = config["database"]
    config["password"] = os.getenv("PG_PASS", "") or config["password"]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(config))

# orm version
# ===========

# import os
# import sys
#
# from sqlalchemy import create_engine
# from sqlalchemy.engine.url import URL
# from sqlalchemy.orm import sessionmaker
#
# from model import Administrator
# from model import Client
# from model import Repository
# from model import Batch
# from model import Product
# from model import Order
# from model import OrderProductAssociation
# from model import Payment
# from utils import read_configuration_file
#
#
# if __name__ == "__main__":
#     config = read_configuration_file()
#     if not config:
#         sys.exit(1)
#     config = config["database"]
#     config["password"] = os.getenv("PG_PASS", "") or config["password"]
#
#     connection_infos = {
#         "drivername": "postgres",
#         "host": config["host"],
#         "port": config["port"],
#         "username": config["username"],
#         "password": config["password"],
#         "database": config["database"]
#     }
#     dsn = str(URL(**connection_infos))
#
#     db_engine = create_engine(dsn, echo=False)
#
#     Session = sessionmaker(bind=db_engine)
#
#     # create basic objects
#
#     session = Session()
#
#     administrator = Administrator(login="admin", first_name="Franck",
#                                   last_name="Barbenoire",
#                                   email_address="contact@franck-barbenoire.fr")
#     session.add(administrator)
#
#     client_1 = Client(login="rabid", first_name="Raymonde", last_name="Bidochon",
#                       email_address="ra.bidochon@binet.namecom",
#                       phone_number="01-40-50-50-01")
#     session.add(client_1)
#     client_2 = Client(login="robid", first_name="Robert", last_name="Bidochon",
#                       email_address="ro.bidochon@binet.namecom",
#                       phone_number="01-40-50-50-02")
#     session.add(client_2)
#
#     repo_1 = Repository(name="Haut village")
#     session.add(repo_1)
#     repo_2 = Repository(name="Bas village")
#     session.add(repo_2)
#
#     product_1 = Product(name="Pain au sarrasin",
#                         description="Pain avec de la faine de sarrasin dedans",
#                         price=5)
#     session.add(product_1)
#     product_2 = Product(name="Pain de seigle",
#                         description="Pain avec de la faine de seigle dedans",
#                         price=4)
#     session.add(product_2)
#
#     batch_1 = Batch(date="2017-06-18 08:00:00", capacity=50)
#     session.add(batch_1)
#     batch_2 = Batch(date="2017-06-19 08:00:00", capacity=50, opened=False)
#     session.add(batch_2)
#
#     session.commit()
#
#     # link basic object between them
#
#     client_1.repository = repo_1
#     client_2.repository = repo_1
#
#     # ---
#     order_1 = Order()
#     session.add(order_1)
#     order_1.client = client_1
#     order_1.batch = batch_1
#
#     poa_1_1 = OrderProductAssociation(quantity=2)
#     session.add(poa_1_1)
#     poa_1_1.product = product_1
#     order_1.products.append(poa_1_1)
#
#     poa_1_2 = OrderProductAssociation(quantity=3)
#     session.add(poa_1_2)
#     poa_1_2.product = product_2
#     order_1.products.append(poa_1_2)
#
#     print("client.first_name =", order_1.client.first_name)
#     for poa in order_1.products:
#         print("quantity =", poa.quantity)
#         print("product =", poa.product.name)
#
#     # ---
#     order_2 = Order()
#     session.add(order_2)
#     order_2.client = client_1
#     order_2.batch = batch_2
#
#     poa_2 = OrderProductAssociation(quantity=3)
#     session.add(poa_2)
#     poa_2.product = product_1
#     order_2.products.append(poa_2)
#
#     payment_2 = Payment(total=10)
#     session.add(payment_2)
#     order_2.payment = payment_2
#
#     # ---
#     order_3 = Order()
#     session.add(order_3)
#     order_3.client = client_2
#     order_3.batch = batch_1
#
#     poa_3 = OrderProductAssociation()
#     session.add(poa_3)
#     poa_3.product = product_1
#     order_3.products.append(poa_3)
#
#     session.commit()
#
#
#     # compute batch load
#     load = 0
#     for order in batch_1.orders:
#         for poa in order.products:
#             load += poa.quantity
#     print("batch 1 load :", load)
#     print("batch 1 capacity :", batch_1.capacity)
#     print("---")
#
#     # compute order total price
#     price = 0
#     for poa in order_1.products:
#         price += poa.product.price * poa.quantity
#     print("order 1 total price :", price)
#     print("---")
#
#     # search for all orders from a client
#     orders = client_1.orders
#     print("{} orders for client {} {}".format(len(orders), client_1.first_name, client_1.last_name))
#     for order in orders:
#         print("order datetime :", order.placed_at)
#     print("---")
#
#     # search for all non payed orders from a client
#     rows = session.query(Client, Order).join(Client.orders).filter(Client.id == client_1.id).filter(Order.payment != None)
#     print("{} non payed orders for client {} {}".format(rows.count(), client_1.first_name, client_1.last_name))
#     for client, order in rows:
#         print("order datetime :", order.placed_at)
#
#     db_engine.dispose()
