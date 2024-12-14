from fastapi import FastAPI
from db_file import init_product_db, init_user_db, get_product_db, get_user_db

init_user_db()
init_product_db()

app = FastAPI()

