from datetime import datetime, timedelta, timezone
import aiofiles
import sqlite3

import websocket
from jose import JWTError, jwt
from typing import Optional
import re
import asyncio

from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from models import User, Products, ProductName
import uvicorn
from db_file import init_product_db, init_user_db, get_product_db, get_user_db, init_bids_db, get_sanctions_db, \
    init_sanctions_db

# ініціалізація БД
init_bids_db()
init_product_db()
init_user_db()
init_sanctions_db()

app = FastAPI()

# Додавання CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key="secret_key_for_sessions")

# Підключення шаблонів
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# конфігурація JWT
SECRET_KEY = 'qwertyy1556'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

auction_chats = {}
ADMIN_CODE = "1234"

# JWT Token Creation
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, 'email': data.get('email')})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def clear_expired_sanctions():
    with get_sanctions_db() as conn:
        conn.execute(
            'UPDATE user_sanctions SET is_active = FALSE WHERE ban_end_time <= ? AND is_active = TRUE',
            (datetime.utcnow(),)
        )
        conn.commit()

def check_admin_role(request: Request):
    role = request.session.get("role", "user")
    if role != "admin":
        raise HTTPException(status_code=403, detail="You do not have permission to perform this action")

# Рендер головної сторінки
@app.get("/", response_class=HTMLResponse)
async def read_html(request: Request):
    role = request.session.get("role", "user")
    return templates.TemplateResponse("main.html", {"request": request, "role": role})

@app.post("/reset_role")
async def reset_role(request: Request):
    request.session["role"] = "user"
    return RedirectResponse("/", status_code=303)

@app.get("/get_role")
async def get_user_role(request: Request):
    role = request.session.get("role", "user")
    return {"role": role}

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

    role = "user"  # За замовчуванням роль користувача
    token = websocket.headers.get("Authorization")
    if token:
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            role = "admin" if user_data.get("role") == "admin" else "user"
        except JWTError:
            await websocket.close(code=4002, reason="Invalid token")
            return

    auction_chats.setdefault(auction_id, []).append({"websocket": websocket, "role": role})

    try:
        while True:
            message = await websocket.receive_text()

            # Логіка для адміністратора
            if role == "admin" and message.startswith("/admin"):
                await handle_admin_command(message, auction_id, role)  # Передаємо роль як аргумент
            else:
                await broadcast_message(auction_id, message)
    except WebSocketDisconnect:
        auction_chats[auction_id] = [
            conn for conn in auction_chats[auction_id] if conn["websocket"] != websocket
        ]
        if not auction_chats[auction_id]:
            del auction_chats[auction_id]


async def handle_admin_command(message: str, auction_id: int, role: str):  # Додаємо роль як аргумент
    command = message.split(" ", 1)
    if len(command) < 2:
        return

    action, content = command[0], command[1]

    # Перевірка чи користувач має роль admin
    if action.startswith("/admin"):
        if role != "admin":
            await websocket.send_text("You don't have permission to use admin commands.")
            return

    if action == "/admin:mute":
        await mute_user(content, auction_id)
    elif action == "/admin:announce":
        await broadcast_message(auction_id, f"Admin Announcement: {content}")


async def mute_user(user_id: str, auction_id: int):
    for connection in auction_chats[auction_id]:
        if connection["role"] == "user" and connection["websocket"].headers.get("User-ID") == user_id:
            await connection["websocket"].close(code=4003, reason="Muted by admin")

async def broadcast_message(auction_id: int, message: str):
    for connection in auction_chats.get(auction_id, []):
        try:
            await connection.send_text(message)
        except:
            pass

@app.get("/get_admin_role", response_class=HTMLResponse)
async def get_admin_role_page():
    async with aiofiles.open("templates/get_admin_role.html", mode="r") as file:
        return await file.read()

@app.post("/get_admin_role")
async def verify_admin_code(admin_code: str = Form(...), request: Request = None):
    if admin_code == ADMIN_CODE:
        request.session["role"] = "admin"
        return RedirectResponse("/", status_code=303)
    else:
        return RedirectResponse("/invalid_code", status_code=303)


@app.get("/get_role")
async def get_user_role(request: Request):
    role = request.session.get("role", "user")
    return {"role": role}


@app.get("/invalid_code", response_class=HTMLResponse)
async def invalid_code_page():
    async with aiofiles.open("templates/invalid_code.html", mode="r") as file:
        return await file.read()


@app.on_event("startup")
async def startup_event():
    print("Сервер успішно запущений!")


@app.on_event("shutdown")
async def shutdown_event():
    print("Сервер завершив роботу.")


# Запуск додатку
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
