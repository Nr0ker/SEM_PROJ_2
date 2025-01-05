from fastapi.responses import HTMLResponse, RedirectResponse, Response
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
from fastapi.websockets import WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
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
auction_chats = {}
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

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

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
from models import UserCreate

from fastapi import Form

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import status

@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Validate input fields using the Pydantic model
        user_data = UserCreate(username=username, full_name=full_name, email=email, password=password)

        # Check if the email or username already exists in the database
        existing_user = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        if existing_user:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Email or Username already exists."
            })

        # Create and save new user
        new_user = User(
            username=user_data.username,
            full_name=user_data.full_name,
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            role="user",
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return RedirectResponse(url="/", status_code=303)

    except ValueError as ve:
        # Handle Pydantic validation exceptions
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": f"Error: {str(ve)}"
        })

    except RequestValidationError as validation_error:
        # Handle FastAPI validation errors
        user_friendly_errors = [
            err['msg'] for err in validation_error.errors()
        ]
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": " | ".join(user_friendly_errors)
        })


@app.post("/token", response_class=HTMLResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    try:
        # Admin login check
        if form_data.username == "admin" and form_data.password == "admin":
            response = RedirectResponse(url="/admin", status_code=303)
            response.set_cookie(key="access_token", value="admin", httponly=True)
            return response

        # Database user validation
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        access_token = create_access_token(data={"sub": user.username})
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="access_token", value=f"{access_token}", httponly=True)
        return response

    except HTTPException as e:
        # Render the login page with the error message
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": e.detail}
        )

@app.get("/logout")
async def logout(response: Response):
    """Handle user logout."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")  # Delete the JWT token cookie
    return response

@app.get("/profile", response_class=HTMLResponse)
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


@app.get('/header', response_class=HTMLResponse)
async def header(request: Request, access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    return templates.TemplateResponse("header.html", {"request": request, "user": user})


@app.get("/register-page", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    if user:
        return templates.TemplateResponse("main.html", {"request": request, "user": user})
    return templates.TemplateResponse("login.html", {"request": request, "user": None})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Додаткові функції
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Сервер стартує...")
    yield
    print("Сервер завершує роботу...")


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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
