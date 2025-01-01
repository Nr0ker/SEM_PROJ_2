from datetime import datetime, timedelta, timezone
import aiofiles
import sqlite3
from jose import JWTError, jwt
from typing import Optional
import re

from fastapi import FastAPI, Depends, HTTPException, status, Form, Request, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket, WebSocketDisconnect

from models import User, Products, ProductName
import uvicorn
from db_file import init_product_db, init_user_db, get_product_db, get_user_db, init_bids_db

init_bids_db()
init_product_db()
init_user_db()


app = FastAPI()
templates = Jinja2Templates(directory="templates")


# Config for JWT
SECRET_KEY = 'qwertyy1556'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

# JWT Token Creation
def get_password_hash(password):
    return pwd_context.hash(password)

# password checking
def verify_password(plait_password, hashed_password):
    return pwd_context.verify(plait_password, hashed_password)


# token creation
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta  # Use timezone-aware UTC datetime
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})  # Set expiration time
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# List of active users
connections = []

# Decode JWT and get current user
def get_current_user(token: str = Cookie(None)):
    if not token:
        print('no token given')
        print(token)
        return None

    # Remove the "Bearer " prefix if present
    token = token.replace("Bearer ", "") if token.startswith("Bearer ") else token

    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        username: str = payload.get("sub")

        if username is None:
            print('no username given')
            return None

        return {"username": username}
    except JWTError:
        raise HTTPException(
            detail="jwt error",
            headers={"WWW-Authenticate": "Bearer"},
        )



# Render main page
@app.get("/", response_class=HTMLResponse)
async def read_html(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/register-page", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Register function
@app.post('/register')
async def register(
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        is_admin: bool = Form(False)
):
    user = User(username=username, email=email, password=password, is_admin=is_admin)
    hashed_password = get_password_hash(user.password)

    with get_user_db() as conn:
        cursor = conn.execute('SELECT * FROM users WHERE email = ?', (user.email,))
        existing_user = cursor.fetchone()

        if existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")

        conn.execute(
            'INSERT INTO users (username, email, hashed_password, is_admin) VALUES(?, ?, ?, ?)',
            (user.username, user.email, hashed_password, user.is_admin)
        )
        conn.commit()

        # Generate JWT token with only username
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.username},  # Only include username (sub)
            expires_delta=access_token_expires
        )

        # Redirect with token in cookie
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="Authorization",
            value=access_token,
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=True,
            samesite="Strict"
        )
        return response



@app.get("/login-page", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Login
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with get_user_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (form_data.username,))
        user = cursor.fetchone()

        if not user or not verify_password(form_data.password, user['hashed_password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Generate the JWT token with only the username (no email)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user['username']},  # Only include username (sub)
            expires_delta=access_token_expires
        )

        # Create a redirect response and set the token as an HTTP-only cookie
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="Authorization",
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=True,  # Use secure cookies in production
            samesite="Strict"  # Adjust based on your needs
        )
        return response



# Function to check if the user is an admin
def is_user_admin(username: str) -> bool:
    with get_user_db() as conn:
        cursor = conn.execute('SELECT is_admin FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()

        if result:
            return result['is_admin']
        return False

# Endpoint to get all products
@app.get('/get_all_products')
def get_all_products(user: dict = Depends(get_current_user)):
    username = user.get("username")
    if not username or not is_user_admin(username):
        raise HTTPException(status_code=403, detail="Access denied: Admins only")

    with get_product_db() as conn:
        cursor = conn.execute('SELECT * FROM products')  # Adjust table name as needed
        products = cursor.fetchall()

    return {"products": products}

# Adding products in db
@app.post('/add_products')
def add_products(product: Products, user: dict = Depends(get_current_user)):
    username = user.get("username")
    if not username or not is_user_admin(username):
        raise HTTPException(status_code=403, detail="Access denied: Admins only")

    curr_price = product.start_price  # Add current price -> will change in future

    with get_product_db() as conn:
        conn.execute(
            '''
            INSERT INTO products (name, desc, start_price, curr_price)
            VALUES (?, ?, ?, ?)
            ''',
            (product.name, product.desc, product.start_price, curr_price)
        )
        conn.commit()

    return {"message": f"Product '{product.name}' added successfully"}

# Mark product as sailed
@app.post('/is_sailed')
def sailed(product: ProductName, user: dict = Depends(get_current_user)):
    username = user.get("username")
    if not username or not is_user_admin(username):
        raise HTTPException(status_code=403, detail="Access denied: Admins only")
    with get_product_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE name = ?', (product.name,))
        existing_product = cursor.fetchone()
        if not existing_product:
            raise HTTPException(status_code=404, detail=f"Product '{product.name}' not found")

        conn.execute(
            '''
            UPDATE products
            SET is_sailed = 1  -- Mark as sailed
            WHERE name = ?
            ''',
            (product.name,)
        )
        conn.commit()

    return {"message": f"Product '{product.name}' marked as sailed successfully"}

# Delete product
@app.delete('/delete_product')
async def delete_product(product: ProductName, user: dict = Depends(get_current_user)):
    username = user.get("username")
    if not username or not is_user_admin(username):
        raise HTTPException(status_code=403, detail="Access denied: Admins only")
    with get_product_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE name = ?', (product.name,))
        existing_product = cursor.fetchone()
        if not existing_product:
            raise HTTPException(status_code=404, detail=f"Product '{product.name}' not found")

        conn.execute(
            '''
            DELETE FROM products
            WHERE name = ?
            ''',
            (product.name,)
        )
        conn.commit()

    return {"message": f"Product '{product.name}' deleted successfully"}

# User adding product into db -> implement in HTML
@app.post('/add_product_user_side')
async def add_product_user_side(product: Products, user: dict = Depends(get_current_user)):
    curr_price = product.start_price  # Add current price -> will change in future

    with get_product_db() as conn:
        conn.execute(
            '''
            INSERT INTO products (name, desc, start_price, curr_price)
            VALUES (?, ?, ?, ?)
            ''',
            (product.name, product.desc, product.start_price, curr_price)
        )
        conn.commit()

    async with aiofiles.open("templates/user_add_product.html", mode='r') as file:
        content = await file.read()
    return content

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
