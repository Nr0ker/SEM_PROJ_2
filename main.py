from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi import FastAPI, HTTPException, Depends, Form, Cookie, UploadFile
from pydantic import BaseModel, EmailStr, Field
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
import aiofiles
import sqlite3
from jose import JWTError, jwt
from typing import Optional
import re
import asyncio

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from models import User, Products, ProductName
import uvicorn
from db_file import init_product_db, init_user_db, get_product_db, get_user_db, init_bids_db

# ініціалізація БД
init_bids_db()
init_product_db()
init_user_db()

app = FastAPI()

# Додавання CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Підключення шаблонів
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

####### db functions ##############
from db_file import init_db, Base, Bid, User, Product, Cart, HistoryOfChanges

# конфігурація JWT
SECRET_KEY = 'qwertyy1556'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

auction_chats = {}

# JWT Token Creation
def get_password_hash(password):
    return pwd_context.hash(password)

# перевірка паролю
def verify_password(plait_password, hashed_password):
    return pwd_context.verify(plait_password, hashed_password)

# створення токену
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, 'email': data.get('email')})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Додаткові функції
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Сервер стартує...")
    yield
    print("Сервер завершує роботу...")

# Рендер головної сторінки
@app.get("/", response_class=HTMLResponse)
async def read_html():
    async with aiofiles.open("templates/main.html", mode='r') as file:
        return await file.read()

# Реєстрація користувача
@app.post('/register')
async def register(user: User):
    hashed_password = get_password_hash(user.password)
    with get_user_db() as conn:
        cursor = conn.execute('SELECT * FROM users WHERE email = ?', (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already in use")
        elif not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', user.email):
            return {'message': 'Invalid email format'}
        conn.execute('INSERT INTO users (username, email, hashed_password, is_admin) VALUES (?, ?, ?, ?)',
                     (user.username, user.email, hashed_password, user.is_admin))
        conn.commit()
    return {"message": "User successfully registered"}

# Логін користувача
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with get_user_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (form_data.username,))
        user = cursor.fetchone()
        if not user or not verify_password(form_data.password, user['hashed_password']):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
        access_token = create_access_token(data={"sub": form_data.username, "email": user['email']})
        return {"access_token": access_token, "token_type": "bearer", 'msg': 'Welcome'}

# Одержання всіх продуктів
@app.get('/get_all_products')
def get_all_products():
    with get_product_db() as conn:
        products = conn.execute('SELECT * FROM products').fetchall()
    return {"products": products}

# Додавання продуктів
@app.post('/add_products')
def add_products(product: Products):
    with get_product_db() as conn:
        conn.execute('INSERT INTO products (name, desc, start_price, curr_price) VALUES (?, ?, ?, ?)',
                     (product.name, product.desc, product.start_price, product.start_price))
        conn.commit()
    return {"message": f"Product '{product.name}' added successfully"}

# Відправка повідомлень для аукціону
@app.websocket("/ws/{auction_id}")
async def websocket_endpoint(websocket: WebSocket, auction_id: int):
    await websocket.accept()
    auction_chats.setdefault(auction_id, []).append(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            await broadcast_message(auction_id, message)
    except WebSocketDisconnect:
        auction_chats[auction_id].remove(websocket)
        if not auction_chats[auction_id]:
            del auction_chats[auction_id]

async def broadcast_message(auction_id: int, message: str):
    for connection in auction_chats.get(auction_id, []):
        try:
            await connection.send_text(message)
        except:
            pass

# Запуск додатку
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
