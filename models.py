from typing import Optional
import re
from pydantic import BaseModel, EmailStr, field_validator


# user validator for db
class User(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_admin: bool

    @field_validator('username', mode='before')
    @classmethod
    def username_validation(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError('Name should be more than 2 letters')
        if not (value[0].isupper() and value[1:].islower()):
            raise ValueError("Your name MUST start with a capital letter and the rest must be lowercase")
        return value

    @field_validator('password', mode='before')
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.fullmatch(r'(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*]).{6,}', value):
            raise ValueError(
                'Password must be at least 6 characters long, contain small and big letters, numbers, and special symbols')
        return value


# idk if i make it but it for products
class Products(BaseModel):
    name: str
    desc: str
    start_price: float


class ProductName(BaseModel):
    name: str





