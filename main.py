from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi import FastAPI, HTTPException, Depends, Form, Cookie, UploadFile
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
import base64

app = FastAPI()

# Set up templates and static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

####### db functions ##############
from db_file import init_db, Base, Bid, User, Product, Cart, HistoryOfChanges

# Database connection
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create the engine with a pool size and connection timeout
engine = create_engine(
    "mysql+pymysql://root:@localhost/broject_db?charset=utf8mb4&connect_timeout=300&read_timeout=300&write_timeout=300",
)
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
        print('No token')
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
async def profile(request: Request, access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@app.get("/index", response_class=HTMLResponse)
async def index(request: Request, access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


# @app.get('', response_class=HTMLResponse)
# async def header(request: Request, access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
#     user = get_current_user_from_token(access_token, db)
#     return templates.TemplateResponse("header.html", {"request": request, "user": user})

from fastapi.responses import StreamingResponse
from io import BytesIO
@app.get("/register-page", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/product_image/{product_id}")
async def get_product_image(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product or not product.photo:
        raise HTTPException(status_code=404, detail="Product or image not found")

    # Convert the binary photo to a stream
    image_stream = BytesIO(product.photo)

    # Assuming the image is in JPEG format; adjust the content type if needed
    return StreamingResponse(image_stream, media_type="image/jpeg")

import base64
# render main_page
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})

    # Get products and categorize them
    big_products = db.query(Product).filter(Product.category == "big").all()
    small_products = db.query(Product).filter(Product.category == "small").all()

    # Categorize products and handle photo encoding
    for product in big_products + small_products:
        if product.curr_price and product.curr_price >= 1000:
            product.category = "big"
        else:
            product.category = "small"

        # Encode photo to Base64 for rendering in HTML
        if product.photo:
            try:
                product.photo = base64.b64encode(product.photo).decode("utf-8")
            except Exception as e:
                print(f"Error encoding product photo: {e}")
                product.photo = None  # Handle errors appropriately

    return templates.TemplateResponse("main.html", {
        "request": request,
        "user": user,
        "big_products": big_products,
        "small_products": small_products
    })


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
# websocket

from typing import List
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()


@app.websocket("/ws/{product_id}")
async def websocket_endpoint(websocket: WebSocket, product_id: int, db: Session = Depends(get_db)):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()

            # Extract details from incoming data
            new_price = data.get("newPrice")
            timestamp = data.get("timestamp")

            # Update the product price in the database
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                product.curr_price = new_price  # Update the current price in the database
                db.commit()

                # Record the price change in the history table
                history_entry = HistoryOfChanges(
                    attached_product_id=product_id,
                    new_price=new_price,
                    timestamp=timestamp
                )
                db.add(history_entry)
                db.commit()

                # Broadcast the new update to all connected clients
                await manager.broadcast({
                    "productId": product_id,
                    "newPrice": new_price,
                    "timestamp": timestamp
                })
            else:
                # Handle the case where the product is not found
                await websocket.send_json({
                    "error": "Product not found"
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)







# Додаткові функції
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("Сервер стартує...")
#     yield
#     print("Сервер завершує роботу...")
#
#
# # Відправка повідомлень для аукціону
# @app.websocket("/ws/{auction_id}")
# async def websocket_endpoint(websocket: WebSocket, auction_id: int):
#     await websocket.accept()
#     auction_chats.setdefault(auction_id, []).append(websocket)
#     try:
#         while True:
#             message = await websocket.receive_text()
#             await broadcast_message(auction_id, message)
#     except WebSocketDisconnect:
#         auction_chats[auction_id].remove(websocket)
#         if not auction_chats[auction_id]:
#             del auction_chats[auction_id]
#
# async def broadcast_message(auction_id: int, message: str):
#     for connection in auction_chats.get(auction_id, []):
#         try:
#             await connection.send_text(message)
#         except:
#             pass

@app.get("/add_product-page", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("add_product.html", {"request": request})



# CRUD FOR PRODUCTS
from fastapi import File

# READ


@app.get("/read_products", response_class=HTMLResponse)
async def read_products(request: Request, access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})

    try:
        products = db.query(Product).filter(Product.user_id_attached == user.id).all()

        # No need to encode photo to Base64, just pass the binary data directly
        for product in products:
            if product.photo:
                try:
                    product.photo = base64.b64encode(product.photo).decode("utf-8")
                except Exception as e:
                    print(f"Error encoding product photo: {e}")
                    product.photo = None  # Handle errors appropriately

        return templates.TemplateResponse("read_products.html", {
            "request": request,
            "products": products
        })
    except Exception as e:
        print(e)
        return templates.TemplateResponse("read_products.html", {
            "request": request,
            "error": f"Error: {str(e)}"
        })


# get product with it`s id

def format_date(timestamp):
    return datetime.fromisoformat(timestamp).strftime('%d/%m/%Y')
@app.get("/product/{product_id}", response_class=HTMLResponse)
async def view_product(product_id: int, request: Request, access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    # Get user from token
    user = get_current_user_from_token(access_token, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})

    # Fetch product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return templates.TemplateResponse("main.html", {"request": request})  # Product not found

    # Fetch price change history
    product_history = db.query(HistoryOfChanges).filter(HistoryOfChanges.attached_product_id == product_id).all()

    # Return the view product page
    return templates.TemplateResponse("view_product.html", {
        "request": request,
        "product": product,
        "user": user,
        "price_updates": product_history  # Pass history to the template
    })



from PIL import Image
import io

# ADD
@app.post('/add_product', response_class=HTMLResponse)
async def add_product(request: Request,
                      name: str = Form(...),
                      desc: str = Form(...),
                      start_price: str = Form(...),
                      photo: Optional[UploadFile] = File(None),
                      access_token: Optional[str] = Cookie(None),
                      db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})

    try:
        # Handle photo, if provided (store as raw binary data)
        photo_data = None
        if photo:
            photo_data = await photo.read()  # Read the photo as raw bytes

        # Default category is None; will update based on price
        category = "small" if float(start_price) < 1000 else "big"

        if photo_data:
            # Compress the image
            img = Image.open(io.BytesIO(photo_data))  # Use photo_data here
            img = img.convert('RGB')  # Convert image to RGB (JPG compatible)

            # Resize the image to a smaller size (optional)
            img.thumbnail((1024, 1024))  # Resize to max 1024x1024

            # Save the image into a buffer with a specific quality
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=85)  # You can adjust quality here
            compressed_image_data = img_byte_arr.getvalue()
        else:
            compressed_image_data = None  # If no photo, set it to None

        # Create the new product object
        new_product = Product(
            name=name,
            desc=desc,
            start_price=float(start_price),
            curr_price=float(start_price),
            photo=compressed_image_data,  # Store the compressed image data as binary
            user_id_attached=user.id,
            category=category
        )

        # Add the product to the database and commit
        db.add(new_product)
        db.commit()
        db.refresh(new_product)

        return RedirectResponse(url="/", status_code=303)

    except Exception as e:
        print(e)
        return templates.TemplateResponse("add_product.html", {
            "request": request,
            "error": f"Error: {str(e)}"
        })


# UPDATE

@app.get('/search_product_update', response_class=HTMLResponse)
async def search_product_update_page(request: Request):
    return templates.TemplateResponse("search_product_update.html", {"request": request})


@app.post('/search_product_update', response_class=HTMLResponse)
async def search_product_update(request: Request,
                                product_name: str = Form(...),
                                db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.name == product_name).first()
    if product:
        return RedirectResponse(url=f"/update_product-page/{product.name}", status_code=303)
    return templates.TemplateResponse("search_product_update.html", {
        "request": request,
        "error": "No product found with the provided name."
    })

@app.get('/update_product-page/{product_name}', response_class=HTMLResponse)
async def update_product_page(request: Request, product_name: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.name == product_name).first()
    if product:
        return templates.TemplateResponse("update_product.html", {"request": request, "product": product})
    return templates.TemplateResponse("update_product.html", {"request": request, "error": "Product not found."})


@app.post('/update_product', response_class=HTMLResponse)
async def update_product(request: Request,
                         name: str = Form(...),
                         desc: str = Form(...),
                         start_price: str = Form(...),
                         photo: Optional[UploadFile] = File(None),
                         access_token: Optional[str] = Cookie(None),
                         db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})

    try:
        # Fetch the product by name and ensure it belongs to the user
        product = db.query(Product).filter(Product.name == name, Product.user_id_attached == user.id).first()
        if not product:
            return templates.TemplateResponse("update_product.html", {
                "request": request,
                "error": "Product not found."
            })

        # Update the product details
        product.desc = desc
        product.start_price = start_price

        # Handle the photo: Only update if a new photo is provided
        if photo is not None and photo.filename:  # Ensure a new photo is uploaded
            product.photo = await photo.read()

        db.commit()
        db.refresh(product)

        return RedirectResponse(url="/read_products", status_code=303)

    except Exception as e:
        print(e)
        return templates.TemplateResponse("update_product.html", {
            "request": request,
            "error": f"Error: {str(e)}"
        })





# DELETE

@app.get('/search_product_delete', response_class=HTMLResponse)
async def search_product_delete_page(request: Request):
    return templates.TemplateResponse("search_product_delete.html", {"request": request})


@app.post('/search_product_delete', response_class=HTMLResponse)
async def search_product_delete(request: Request,
                                product_name: str = Form(...),
                                db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.name == product_name).first()
    if product:
        return RedirectResponse(url=f"/delete_product-page/{product.name}", status_code=303)
    return templates.TemplateResponse("search_product_delete.html", {
        "request": request,
        "error": "No product found with the provided name."
    })


@app.get('/delete_product-page/{product_name}', response_class=HTMLResponse)
async def delete_product_page(request: Request, product_name: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.name == product_name).first()
    if product:
        return templates.TemplateResponse("delete_product.html", {"request": request, "product": product})
    return templates.TemplateResponse("delete_product.html", {"request": request, "error": "Product not found."})


@app.post('/delete_product/{product_name}', response_class=HTMLResponse)
async def delete_product(request: Request,
                         product_name: str,
                         access_token: Optional[str] = Cookie(None),
                         db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})

    try:
        product = db.query(Product).filter(Product.name == product_name, Product.user_id_attached == user.id).first()
        if not product:
            return templates.TemplateResponse("delete_product.html", {
                "request": request,
                "error": "Product not found."
            })

        db.delete(product)
        db.commit()
        return RedirectResponse(url="/read_products", status_code=303)

    except Exception as e:
        print(e)
        return templates.TemplateResponse("delete_product.html", {
            "request": request,
            "error": f"Error: {str(e)}"
        })



###################### USER SIDE -> PROFILE, CART ETC
@app.get("/add_to_cart/{user_id}/{product_id}", response_class=HTMLResponse)
async def add_to_cart(user_id: int, product_id: int, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if the product is already in the user's cart
    cart_item = db.query(Cart).filter(Cart.user_id == user_id, Cart.product_id == product_id).first()

    if cart_item:
        # If the product is already in the cart, increase the quantity by 1
        cart_item.quantity += 1
    else:
        # Otherwise, create a new cart item
        cart_item = Cart(user_id=user_id, product_id=product_id, quantity=1)
        db.add(cart_item)

    # Commit the transaction
    db.commit()
    return RedirectResponse(url=f"/cart/{user_id}", status_code=303)


# Show user's cart
@app.get("/cart/{user_id}")
async def view_cart(request: Request, user_id: int, db: Session = Depends(get_db)):
    # Get the user and their cart items
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch all cart items with the associated products
    cart_items = db.query(Cart).filter(Cart.user_id == user_id).all()

    # Add photo encoding for each product in the cart
    for cart_item in cart_items:
        product = cart_item.product  # Assuming Cart has a relationship to Product
        if product.photo:
            try:
                product.photo = base64.b64encode(product.photo).decode("utf-8")
            except Exception as e:
                print(f"Error encoding product photo: {e}")
                product.photo = None  # Handle errors appropriately

    # Calculate total price
    total_price = sum(cart_item.quantity * cart_item.product.curr_price for cart_item in cart_items)

    return templates.TemplateResponse("cart.html", {
        "request": request,
        "user": user,
        "cart_items": cart_items,
        "total_price": total_price,
    })

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, access_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    user = get_current_user_from_token(access_token, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("settings.html", {"request": request, "user": user})



@app.post("/update_username")
async def update_username(
    old_username: str = Form(...),
    new_username: str = Form(...),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    user = get_current_user_from_token(access_token, db)
    if not user or user.username != old_username:
        raise HTTPException(status_code=400, detail="Invalid current username")

    user.username = new_username
    db.commit()
    db.refresh(user)
    return RedirectResponse(url="/settings", status_code=303)



@app.post("/update_email")
async def update_email(
    old_email: str = Form(...),
    new_email: str = Form(...),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    user = get_current_user_from_token(access_token, db)
    if not user or user.email != old_email:
        raise HTTPException(status_code=400, detail="Invalid current email")

    user.email = new_email
    db.commit()
    db.refresh(user)
    return RedirectResponse(url="/settings", status_code=303)




@app.post("/update_password")
async def update_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    user = get_current_user_from_token(access_token, db)
    if not user or not verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid current password")

    user.hashed_password = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return RedirectResponse(url="/settings", status_code=303)



@app.post("/update-settings")
async def update_settings(
    old_username: str = Form(...),
    new_username: str = Form(None),
    old_password: str = Form(...),
    new_password: str = Form(None),
    old_email: str = Form(...),
    new_email: str = Form(None),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    user = get_current_user_from_token(access_token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Verify old username and password
    # if user.username == old_username or not pwd_context.verify(old_password, user.hashed_password):
    #     raise HTTPException(status_code=400, detail="Invalid current username or password")

    # Update username
    if new_username:
        if db.query(User).filter(User.username == new_username).first():
            raise HTTPException(status_code=400, detail="Username already exists")
        user.username = new_username

    # Update password
    if new_password:
        user.hashed_password = pwd_context.hash(new_password)

    # Update email
    if new_email:
        if db.query(User).filter(User.email == new_email).first():
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = new_email

    # Commit changes to the database
    db.commit()
    db.refresh(user)

    return RedirectResponse(url="/settings", status_code=303)

# @app.post("/update_price/{product_id}/{new_price}")
# async def update_price(product_id: int, new_price: float, db: Session = Depends(get_db)):
#     product = db.query(Product).filter(Product.id == product_id).first()
#     if product:
#         product.current_price = new_price
#         db.commit()
#         db.refresh(product)
#         return {"message": "Price updated successfully"}
#     return {"message": "Product not found"}






if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
