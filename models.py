from pydantic import BaseModel, EmailStr, Field, validator, field_validator
import re


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator('password', mode='before')
    def validate_password(cls, value):
        """
        Validate password strength:
        - At least 8 characters
        - Includes uppercase, lowercase, number, and special character
        """
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', value):
            raise ValueError(
                "Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character."
            )
        return value
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
    photo: Optional[bytes] = None


class ProductName(BaseModel):
    name: str