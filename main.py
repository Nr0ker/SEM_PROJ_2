from datetime import datetime, timedelta, timezone
import aiofiles
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
import sqlite3
from jose import JWTError, jwt
from typing import Optional
import re
from models import User
import uvicorn
from db_file import init_product_db, init_user_db, get_product_db, get_user_db


init_user_db()
init_product_db()

app = FastAPI()
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
outh2_scheme = OAuth2PasswordBearer(tokenUrl='token')


# config of JWT
SECRET_KEY = 'qwertyy1556'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# list of active users
connections = []
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
outh2_scheme = OAuth2PasswordBearer(tokenUrl='token')

# render main page
@app.get("/", response_class=HTMLResponse)
async def read_html():
    # Open and read the HTML file asynchronously
    async with aiofiles.open("main.html", mode='r') as file:
        content = await file.read()
    return content


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
                conn.execute('INSERT INTO users (username, email, hashed_password) VALUES(?, ?, ?)',
                             (user.username, user.email, hashed_password))
                conn.commit()
                return {"message": "User successfully registered"}
            except sqlite3.Error as s:
                raise HTTPException(status_code=400, detail="Something went wrong")


# login
@app.post("/login")
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
            data={"sub": form_data.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
