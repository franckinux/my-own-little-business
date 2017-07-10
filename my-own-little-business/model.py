from datetime import datetime
import enum

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class PayedStatusEnum(enum.Enum):
    not_payed = 0
    payed_by_check = 1
    payed_inline = 2


class Administrator(Base):
    __tablename__ = "administrator"

    id = Column(Integer, primary_key=True)
    login = Column(String, nullable=False, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    email_address = Column(String, nullable=False)
    receive_notifications = Column(Boolean, default=True)

    def __repr__(self):
        return "<Administrator (login={})>".format(self.login)


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True)
    disabled = Column(Boolean, default=True)
    login = Column(String, nullable=False, unique=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email_address = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    wallet = Column(Numeric(precision=8, scale=2, asdecimal=True), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=True)

    repository_id = Column(Integer, ForeignKey("repository.id"))
    repository = relationship("Repository", back_populates="clients")

    orders = relationship("Order", back_populates="client")

    def __repr__(self):
        return "<Client (login={}, first_name={}, last_name={})>".format(
            self.login, self.first_name, self.last_name
        )


class Repository(Base):
    __tablename__ = "repository"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    opened = Column(Boolean, default=True)

    clients = relationship("Client", back_populates="repository")

    def __repr__(self):
        return "<Repository (name={})>".format(self.name)


class Batch(Base):
    __tablename__ = "batch"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, unique=True)
    capacity = Column(Integer, nullable=False)
    opened = Column(Boolean, default=True)

    orders = relationship("Order", back_populates="batch")

    def __repr__(self):
        return "<Batch (date={}, opened={})>".format(self.date, self.opened)


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    price = Column(Numeric(precision=8, scale=2, asdecimal=True), nullable=False)
    load = Column(Numeric(precision=8, scale=2, asdecimal=True), default=1)
    available = Column(Boolean, default=True)

    def __repr__(self):
        return "<Product (name={}, price={})>".format(self.name, self.price)


class Order(Base):
    __tablename__ = "order_"

    id = Column(Integer, primary_key=True)
    placed_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("OrderProductAssociation")

    client_id = Column(Integer, ForeignKey("client.id"))
    client = relationship("Client", back_populates="orders")

    batch_id = Column(Integer, ForeignKey("batch.id"))
    batch = relationship("Batch", back_populates="orders")

    payment_id = Column(Integer, ForeignKey("payment.id"))
    payment = relationship("Payment", back_populates="orders")

    def __repr__(self):
        return "<Order (placed_at={})>".format(self.placed_at)


class OrderProductAssociation(Base):
    __tablename__ = "order_product_association"

    quantity = Column(Integer, default=1)

    order_id = Column(Integer, ForeignKey("order_.id"), primary_key=True)
    product_id = Column(Integer, ForeignKey("product.id"), primary_key=True)

    product = relationship("Product")


class Payment(Base):
    __tablename__ = "payment"

    id = Column(Integer, primary_key=True)
    total = Column(Numeric(precision=8, scale=2, asdecimal=True), nullable=False)
    payed_at = Column(DateTime, nullable=True)
    mode = Column(Enum(PayedStatusEnum), nullable=True, default=PayedStatusEnum.not_payed)
    reference = Column(String, nullable=True)

    orders = relationship("Order", back_populates="payment")

    def __repr__(self):
        return "<Payment (total={}, payed_at={})>".format(self.total, self.payed_at)
