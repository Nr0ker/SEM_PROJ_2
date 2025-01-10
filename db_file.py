import sqlite3
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# user db
def get_user_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

class User(Base):
    __tablename__ = "users"

def init_user_db():
    conn = get_user_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            hashed_password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0
        )
    ''')

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)  # Quantity of the product in the cart

# product db
def get_product_db():
    conn = sqlite3.connect('products.db')
    conn.row_factory = sqlite3.Row
    return conn

class HistoryOfChanges(Base):
    __tablename__ = "history_of_changes"

def init_product_db():
    conn = get_product_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            desc TEXT NOT NULL,
            start_price FLOAT NOT NULL,
            curr_price FLOAT,
            is_sailed BOOLEAN DEFAULT 0,
            photo LONGBLOB
        )
    ''')
    print('2')


def get_bids_db():
    conn = sqlite3.connect('bids.db')
    conn.row_factory = sqlite3.Row
    return conn

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    desc = Column(String(1000), nullable=False)
    start_price = Column(Float, nullable=False)
    curr_price = Column(Float)
    highest_bidder_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    is_sailed = Column(Boolean, default=False)
    in_stock = Column(Boolean, default=False)
    photo = Column(LONGBLOB)  # LONGBLOB for large images
    user_id_attached = Column(Integer, ForeignKey('users.id'))
    category = Column(String(50), nullable=True)  # "big" or "small"

def init_bids_db():
    conn = get_bids_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY,          
            user_id INTEGER NOT NULL,         
            product_id INTEGER NOT NULL,  
            bid_amount REAL NOT NULL,        
            bid_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
            FOREIGN KEY (user_id) REFERENCES users(id),   
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    ''')
    conn.commit()
    conn.close()
    print('1')


init_bids_db()
init_product_db()
init_user_db()