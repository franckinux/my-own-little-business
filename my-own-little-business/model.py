from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Administrator(Base):
    __tablename__ = "administrator"

    id = Column(Integer, primary_key=True)
    login = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    email_address = Column(String, nullable=False)
    receive_notifications = Column(Boolean, default=True)

    def __init__(self, login, first_name, last_name, email_address,
                 receive_notifications=True):
        self.login = login
        self.first_name = first_name
        self.last_name = last_name
        self.email_address = email_address
        self.receive_notifications = receive_notifications

    def __repr__(self):
        return "<Administrator (login=%s)>".format(self.login)


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    login = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email_address = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    receive_bill = Column(Boolean, default=False)
    wallet = Column(Numeric(precision=8, scale=2, asdecimal=True), default=0)

    repository_id = Column(Integer, ForeignKey("repository.id"))
    repository = relationship("Repository", back_populates="clients")

    orders = relationship("Order", back_populates="client")

    def __init__(self, login, first_name, last_name, email_address, phone_number,
                 receive_bill=True, wallet=0):
        self.login = login
        self.first_name = first_name
        self.last_name = last_name
        self.email_address = email_address
        self.phone_number = phone_number
        self.receive_bill = receive_bill
        self.wallet = wallet

    def __repr__(self):
        return "<Client (login=%s, first_name=%s, last_name=%s)>".format(
            self.login, self.first_name, self.last_name
        )


class Repository(Base):
    __tablename__ = "repository"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    clients = relationship("Client", back_populates="repository")

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Repository (name=%s)>".format(self.name)


class Batch(Base):
    __tablename__ = "batch"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    capacity = Column(Integer, nullable=False)
    opened = Column(Boolean, default=True)

    orders = relationship("Order", back_populates="batch")

    def __init__(self, date, capacity, opened=True):
        self.date = date
        self.capacity = capacity
        self.opened = opened

    def __repr__(self):
        return "<Batch (date=%s, opened=%s)>".format(self.date, self.opened)


product_order_atbl = Table(
    "order_product_association",
    Base.metadata,
    Column("order_id", Integer, ForeignKey("order.id")),
    Column("product_id", Integer, ForeignKey("product.id")),
    Column("quantity", Integer, default=1)
)


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(Numeric(precision=8, scale=2, asdecimal=True), nullable=False)

    def __init__(self, name, description, price):
        self.name = name
        self.description = description
        self.price = price

    def __repr__(self):
        return "<Product (name=%s, price=%s)>".format(self.name, self.price)


class Order(Base):
    __tablename__ = "order"

    id = Column(Integer, primary_key=True)
    order_placed_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", secondary=product_order_atbl)

    client_id = Column(Integer, ForeignKey("client.id"))
    client = relationship("Client", back_populates="orders")

    batch_id = Column(Integer, ForeignKey("batch.id"))
    batch = relationship("Batch", back_populates="orders")

    payment_id = Column(Integer, ForeignKey("payment.id"))
    payment = relationship("Payment", back_populates="orders")

    def __repr__(self):
        return "<Product (order_placed_at=%s)>".format(self.order_placed_at)


class Payment(Base):
    __tablename__ = "payment"

    id = Column(Integer, primary_key=True)
    total = Column(Numeric(precision=8, scale=2, asdecimal=True), nullable=False)
    payed_at = Column(DateTime, nullable=True)
    mode = Column(String, nullable=True)
    reference = Column(String, nullable=True)

    orders = relationship("Order", back_populates="payment")

    def __init__(self, total):
        self.total = total

    def __repr__(self):
        return "<Payment (total=%s, payed_at=%s)>".format(self.total, self.payed_at)
