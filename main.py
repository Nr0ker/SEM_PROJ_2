from fastapi import FastAPI
from db_file import init_product_db, init_user_db, get_product_db, get_user_db
import uvicorn
import websocket

init_user_db()
init_product_db()

app = FastAPI()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)