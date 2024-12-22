from datetime import datetime, timedelta, timezone
import aiofiles
import sqlite3
from jose import JWTError, jwt
from typing import Optional
import re

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from fastapi.websockets import WebSocket, WebSocketDisconnect

from models import User, Products, ProductName
import uvicorn
from db_file import init_product_db, init_user_db, get_product_db, get_user_db, init_bids_db

init_bids_db()
init_product_db()
init_user_db()

app = FastAPI()

# config of JWT
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    # Include the email in the token payload
    to_encode.update({'email': data.get('email')})  # Add email to the token payload
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# list of active users
connections = []

# render main page
@app.get("/", response_class=HTMLResponse)
async def read_html():
    # Open and read the HTML file asynchronously
    async with aiofiles.open("main.html", mode='r') as file:
        content = await file.read()
    return content


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        email: str = payload.get("email")  # Extract email from the payload

        if username is None or email is None:  # Check for both username and email
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Debugging - Print to check the decoded payload
        print(f"Decoded JWT payload: {payload}")

        return {"username": username, "email": email}  # Return username and email
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# register function
@app.post('/register')
async def register(user: User):
    hashed_password = get_password_hash(user.password)
    with get_user_db() as conn:
        cursor = conn.execute('SELECT * FROM users WHERE email = ?', (user.email,))
        existing_user = cursor.fetchone()
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        regex_email = re.match(email_regex, user.email) is not None
        if not regex_email:
            return {'message': 'Your email is not valid, please use an email like useremail@gmail.com'}
        elif existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")
        else:
            try:
                conn.execute('INSERT INTO users (username, email, hashed_password, is_admin) VALUES(?, ?, ?, ?)',
                             (user.username, user.email, hashed_password, user.is_admin))
                conn.commit()
                return {"message": "User successfully registered"}
            except sqlite3.Error as s:
                raise HTTPException(status_code=400, detail="Something went wrong")


# login
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

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username, "email": user['email']}, expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer", 'msg': 'Welcome sir'}


# Function to check if the user is an admin
def is_user_admin(email: str) -> bool:
    with get_user_db() as conn:
        cursor = conn.execute('SELECT is_admin FROM users WHERE email = ?', (email,))
        result = cursor.fetchone()

        if result:
            return result['is_admin']
        return False


# Endpoint to get all products
@app.get('/get_all_products')
def get_all_products(user: dict = Depends(get_current_user)):
    email = user.get("email")  # Ensure `email` is passed in the JWT payload
    if not email or not is_user_admin(email):
        raise HTTPException(status_code=403, detail="Access denied: Admins only")

    with get_product_db() as conn:
        cursor = conn.execute('SELECT * FROM products')  # Adjust table name as needed
        products = cursor.fetchall()

    return {"products": products}


# adding products in db
@app.post('/add_products')
def add_products(product: Products, user: dict = Depends(get_current_user)):
    email = user.get("email")  # Ensure `email` is passed in the JWT payload
    if not email or not is_user_admin(email):
        raise HTTPException(status_code=403, detail="Access denied: Admins only")

    curr_price = product.start_price # add current price -> will change in future

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


# is sailed status
@app.post('/is_sailed')
def sailed(product: ProductName, user : dict = Depends(get_current_user)):
    email = user.get("email")  # Ensure `email` is passed in the JWT payload
    if not email or not is_user_admin(email):
        raise HTTPException(status_code=403, detail="Access denied: Admins only")
    with get_product_db() as conn:
        cursor = conn.cursor()
        #check if user exist
        cursor.execute('SELECT * FROM products WHERE name = ?', (product.name,))
        existing_product = cursor.fetchone()
        if not existing_product:
            raise HTTPException(status_code=404, detail=f"Product '{product.name}' not found")

        # Update
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

# delete product from db ->  delete from db after sailing product
@app.delete('/delete_product')
def delete_product(product: ProductName, user : dict = Depends(get_current_user)):
    email = user.get("email")  # Ensure `email` is passed in the JWT payload
    if not email or not is_user_admin(email):
        raise HTTPException(status_code=403, detail="Access denied: Admins only")
    with get_product_db() as conn:
        cursor = conn.cursor()
        # check if user exist
        cursor.execute('SELECT * FROM products WHERE name = ?', (product.name,))
        existing_product = cursor.fetchone()
        if not existing_product:
            raise HTTPException(status_code=404, detail=f"Product '{product.name}' not found")

        # Delete
        conn.execute(
            '''
            DELETE FROM products
            WHERE name = ?
            ''',
            (product.name,)
        )
        conn.commit()

    return {"message": f"Product '{product.name}' deleted successfully"}


# # update produkt from user_part
# def update_product(product: Products):
#     with get_product_db() as conn:
#         cursor = conn.cursor()
#         # check if user exist
#         cursor.execute('SELECT * FROM products WHERE name = ?', (product.name,))
#         existing_product = cursor.fetchone()
#         if not existing_product:
#             raise HTTPException(status_code=404, detail=f"Product '{product.name}' not found")
#
#         # Delete
#         conn.execute(
#             '''
#             DELETE FROM products
#             WHERE name = ?
#             ''',
#             (product.name,)
#         )
#         conn.commit()
#
#     return {"message": f"Product '{product.name}' deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
