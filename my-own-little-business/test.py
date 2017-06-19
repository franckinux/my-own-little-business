import os
import sys

from sqlalchemy import create_engine
import sqlalchemy as sa
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

from model import Administrator
from model import Base
from model import Client
from model import Repository
from model import Batch
from model import Product
from model import Order
from model import Payment
from utils import read_configuration_file


if __name__ == "__main__":
    config = read_configuration_file()
    if not config:
        sys.exit(1)
    config = config["database"]
    config["password"] = os.getenv("PG_PASS", "") or config["password"]

    connection_infos = {
        "drivername": "postgres",
        "host": config["host"],
        "port": config["port"],
        "username": config["username"],
        "password": config["password"],
        "database": config["database"]
    }
    dsn = str(URL(**connection_infos))

    engine = create_engine(dsn, echo=True)

    Session = sessionmaker(bind=engine)

    # create basic objects

    session = Session()

    administrator = Administrator(login="admin", first_name="Franck",
                                  last_name="Barbenoire",
                                  email_address="contact@franck-barbenoire.fr")
    session.add(administrator)

    client_1 = Client(login="rabid", first_name="Raymonde", last_name="Bidochon",
                      email_address="ra.bidochon@binet.namecom",
                      phone_number="01-40-50-50-01")
    session.add(client_1)
    client_2 = Client(login="robid", first_name="Robert", last_name="Bidochon",
                      email_address="ro.bidochon@binet.namecom",
                      phone_number="01-40-50-50-02")
    session.add(client_2)

    repo_1 = Repository(name="Haut village")
    session.add(repo_1)
    repo_2 = Repository(name="Bas village")
    session.add(repo_2)

    product_1 = Product(name="Pain au sarrasin",
                        description="Pain avec de la faine de sarrasin dedans",
                        price=5)
    session.add(product_1)
    product_2 = Product(name="Pain de seigle",
                        description="Pain avec de la faine de seigle dedans",
                        price=4)
    session.add(product_2)

    batch_1 = Batch(date="2017-06-18 08:00:00", capacity=50)
    session.add(batch_1)
    batch_2 = Batch(date="2017-06-19 08:00:00", capacity=50, opened=False)
    session.add(batch_2)

    session.commit()

    # link basic object between them

    Session = sessionmaker(bind=engine)
    client_1.repository = repo_1
    client_2.repository = repo_1

    # order_1 = Order()
    # session.add(order_1)
    # order_1.client = client_1
    # order_1.batch = batch_1
    # order_1.products.append((product_1, 2, "2017-06-18 22:00:00"))
    # order_1.products.append((product_2, 3))

    # order_2 = Order()
    # session.add(order_2)
    # order_2.client = client_1
    # order_2.products.append((product_1, 1))
    # order_2.batch = batch_2
    #
    # order_3 = Order()
    # session.add(order_3)
    # order_3.client = client_2
    # order_1.products.append((product_1, 1))
    # order_3.batch = batch_1

    session.commit()

    engine.dispose()
