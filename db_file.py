import sqlite3

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
            is_admin BOOLEAN NOT NULL DEFAULT 0
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
            curr_price FLOAT  NOT NULL,
            is_sailed TEXT NOT NULL,
            photo LONGBLOB
        )
    ''')
