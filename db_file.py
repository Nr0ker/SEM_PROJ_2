from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, BLOB, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


# User table model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False, default="Anonymous")
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    profile_photo = Column(BLOB)
    role = Column(String(50), nullable=False, default="user")
    disabled = Column(Boolean, default=False)

    # Relationships
    products = relationship("Product", back_populates="owner")
    bids = relationship("Bid", back_populates="user")


# Product table model
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    desc = Column(String(1000), nullable=False)
    start_price = Column(Float, nullable=False)
    curr_price = Column(Float)
    is_sailed = Column(Boolean, default=False)
    in_stock = Column(Boolean, default=False)
    photo = Column(BLOB)
    user_id_attached = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="products")
    bids = relationship("Bid", back_populates="product")


# Bid table model
class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True)
    bid_amount = Column(Float, nullable=False)
    bid_time = Column(DateTime, default=func.now())
    product_id_attached = Column(Integer, ForeignKey('products.id'), nullable=False)
    user_id_attached = Column(Integer, ForeignKey('users.id'), nullable=False)
    username_attached = Column(String(150), nullable=False)

    # Relationships
    user = relationship("User", back_populates="bids")
    product = relationship("Product", back_populates="bids")


def init_db():
    engine = create_engine('sqlite:///database.db')  # Update with your actual DB URL
    Base.metadata.create_all(bind=engine)


