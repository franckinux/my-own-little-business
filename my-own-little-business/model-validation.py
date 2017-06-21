import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

from model import Administrator
from model import Client
from model import Repository
from model import Batch
from model import Product
from model import Order
from model import OrderProductAssociation
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

    engine = create_engine(dsn, echo=False)

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

    client_1.repository = repo_1
    client_2.repository = repo_1

    # ---
    order_1 = Order()
    session.add(order_1)
    order_1.client = client_1
    order_1.batch = batch_1

    poa_1_1 = OrderProductAssociation(quantity=2)
    session.add(poa_1_1)
    poa_1_1.product = product_1
    order_1.products.append(poa_1_1)

    poa_1_2 = OrderProductAssociation(quantity=3)
    session.add(poa_1_2)
    poa_1_2.product = product_2
    order_1.products.append(poa_1_2)

    print("client.first_name =", order_1.client.first_name)
    for poa in order_1.products:
        print("quantity =", poa.quantity)
        print("product =", poa.product.name)

    # ---
    order_2 = Order()
    session.add(order_2)
    order_2.client = client_1
    order_2.batch = batch_2

    poa_2 = OrderProductAssociation(quantity=3)
    session.add(poa_2)
    poa_2.product = product_1
    order_2.products.append(poa_2)

    payment_2 = Payment(total=10)
    session.add(payment_2)
    order_2.payment = payment_2

    # ---
    order_3 = Order()
    session.add(order_3)
    order_3.client = client_2
    order_3.batch = batch_1

    poa_3 = OrderProductAssociation()
    session.add(poa_3)
    poa_3.product = product_1
    order_3.products.append(poa_3)

    session.commit()


    # compute batch load
    load = 0
    for order in batch_1.orders:
        for poa in order.products:
            load += poa.quantity
    print("batch 1 load :", load)
    print("batch 1 capacity :", batch_1.capacity)
    print("---")

    # compute order total price
    price = 0
    for poa in order_1.products:
        price += poa.product.price * poa.quantity
    print("order 1 total price :", price)
    print("---")

    # search for all orders from a client
    orders = client_1.orders
    print("{} orders for client {} {}".format(len(orders), client_1.first_name, client_1.last_name))
    for order in orders:
        print("order datetime :", order.placed_at)
    print("---")

    # search for all non payed orders from a client
    rows = session.query(Client, Order).join(Client.orders).filter(Client.id == client_1.id).filter(Order.payment != None)
    print("{} orders for client {} {}".format(rows.count(), client_1.first_name, client_1.last_name))
    for client, order in rows:
        print("order datetime :", order.placed_at)

    engine.dispose()
