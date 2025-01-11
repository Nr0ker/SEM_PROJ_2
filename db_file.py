import pymysql
import pytz
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()




# Підключення до MySQL без бази даних
connection = pymysql.connect(
    host='localhost',
    user='root',
    password='Ledyshk@832'
)

try:
    with connection.cursor() as cursor:
        # Створення бази даних, якщо вона ще не існує
        cursor.execute("CREATE DATABASE IF NOT EXISTS broject_db")
        print("Database created or already exists.")
finally:
    connection.close()

# Тепер підключення до бази даних broject_db
engine = create_engine(
    "mysql+pymysql://root:Ledyshk%40832@localhost/broject_db"
)

# Створення всіх таблиць
Base.metadata.create_all(bind=engine)

# User table model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False, default="Anonymous")
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    profile_photo = Column(LONGBLOB)
    role = Column(String(50), nullable=False, default="user")
    disabled = Column(Boolean, default=False)

    # Relationships
    products = relationship(
        "Product",
        back_populates="owner",
        foreign_keys="Product.user_id_attached",  # Вказуємо конкретний зовнішній ключ
    )
    bids = relationship("Bid", back_populates="user")
    cart_items = relationship("Cart", back_populates="user")


# Cart class
class Cart(Base):
    __tablename__ = "cart"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)

    # Relationships
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product")


class HistoryOfChanges(Base):
    __tablename__ = "history_of_changes"

    id = Column(Integer, primary_key=True, index=True)
    attached_product_id = Column(Integer, ForeignKey("products.id"))
    new_price = Column(Float, nullable=False)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)  # UTC time without microseconds

    product = relationship("Product", back_populates="history")


# Product class
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    desc = Column(String(1000), nullable=False)
    start_price = Column(Float, nullable=False)
    curr_price = Column(Float)
    highest_bidder_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    is_sailed = Column(Boolean, default=False)
    in_stock = Column(Boolean, default=False)
    photo = Column(LONGBLOB)
    user_id_attached = Column(Integer, ForeignKey('users.id'))
    category = Column(String(50), nullable=True)

    # Relationships
    owner = relationship(
        "User",
        back_populates="products",
        foreign_keys=[user_id_attached],  # Вказуємо конкретний зовнішній ключ для власника
    )
    highest_bidder = relationship(
        "User",
        foreign_keys=[highest_bidder_id],  # Вказуємо зовнішній ключ для найвищого ставки
    )
    bids = relationship("Bid", back_populates="product")
    history = relationship("HistoryOfChanges", back_populates="product")


class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, default=1)
    bid_time = Column(DateTime, server_default=func.now())
    product_id_attached = Column(Integer, ForeignKey('products.id'), nullable=False)
    user_id_attached = Column(Integer, ForeignKey('users.id'), nullable=False)
    username_attached = Column(String(150), nullable=False)

    # Relationships
    user = relationship("User", back_populates="bids")
    product = relationship("Product", back_populates="bids")


def init_db():
    engine = create_engine(
        "mysql+pymysql://root:Ledyshk%40832@localhost/broject_db?charset=utf8mb4&connect_timeout=300&read_timeout=300&write_timeout=300"
    )
    Base.metadata.create_all(bind=engine)
    print("Database and tables created successfully!")


if __name__ == "__main__":
    init_db()  # Initialize the database and create the tables
