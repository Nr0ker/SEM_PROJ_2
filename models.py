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


# idk if i make it but it for products
class Products(BaseModel):
    name: str
    desc: str
    start_price: float
    photo: Optional[bytes] = None


class ProductName(BaseModel):
    name: str




class ProductDetails(BaseModel):
    id: int
    name: str
    desc: str
    curr_price: float
    photo: Optional[str]  # Фото в base64