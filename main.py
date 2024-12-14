import aiofiles
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from websocket import WebSocket
from db_file import init_product_db, init_user_db, get_product_db, get_user_db
import uvicorn
import websocket
from passlib.context import CryptContext
from pathlib import Path

init_user_db()
init_product_db()

app = FastAPI()
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
outh2_scheme = OAuth2PasswordBearer(tokenUrl='token')


def get_password_hash(password):
    return pwd_context.hash(password)
 # password checking
def verify_password(plait_password, hashed_password):
    return pwd_context.verify(plait_password, hashed_password)


# BASE_DIR = Path(__file__).resolve().parent
# HTML_FILE_PATH = BASE_DIR / "main.html"

@app.get("/", response_class=HTMLResponse)
async def read_html():
    # Open and read the HTML file asynchronously
    async with aiofiles.open("main.html", mode='r') as file:
        content = await file.read()
    return content


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)