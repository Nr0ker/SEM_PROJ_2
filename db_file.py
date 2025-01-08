import sqlite3
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# user db
def get_user_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn


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


# product db
def get_product_db():
    conn = sqlite3.connect('products.db')
    conn.row_factory = sqlite3.Row
    return conn


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


def get_sanctions_db():
    conn = sqlite3.connect("blocked_users.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_sanctions_db():
    conn = get_sanctions_db()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_sanctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        ban_type TEXT,  
        reason TEXT,
        ban_start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ban_end_time TIMESTAMP,
        mute_duration INTEGER,  
        warning_count INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    ''')

    conn.commit()
    conn.close()


init_sanctions_db()
init_bids_db()
init_product_db()
init_user_db()