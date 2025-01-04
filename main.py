from fastapi import FastAPI, Depends, HTTPException, status, Form, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlite3 import Connection
from fastapi import FastAPI, HTTPException, Depends, Form, Cookie
from pydantic import BaseModel, EmailStr, Field
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

# FastAPI app
app = FastAPI()

# Set up templates and static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

####### db functions ##############
from db_file import init_db, Base, Bid, User, Product

# Database connection
DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

####### authorization functions ##############

# Configurations
SECRET_KEY = 'qwertyy1556'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_current_user_from_token(token: Optional[str], db: Session):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None
####### login + register functions ##############

# Routes
@app.post("/register")
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = get_password_hash(password)

    # Default role can be "user" or any role you want
    new_user = User(username=username, email=email, hashed_password=hashed_password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RedirectResponse(url="/", status_code=303)


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Проверка на специальные данные администратора
    if form_data.username == "admin" and form_data.password == "admin":
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(key="access_token", value="admin", httponly=True)
        return response

    # Проверка в базе данных
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=f"{access_token}", httponly=True)
    return response

@app.get("/logout")
async def logout(response: Response):
    """Handle user logout."""
    response = RedirectResponse(url="/login-page", status_code=302)
    response.delete_cookie("access_token")  # Delete the JWT token cookie
    return response

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    if user:
        return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": None})

@app.get("/index", response_class=HTMLResponse)
async def read_root(request: Request, access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    if user:
        return templates.TemplateResponse("index.html", {"request": request, "user": user})
    return templates.TemplateResponse("index.html", {"request": request, "user": None})


@app.get("/register-page", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
