from typing import Optional

from pydantic import BaseModel, EmailStr


class Login(BaseModel):
    """
    Login request schema
    """
    email: EmailStr
    password: str


class PasswordReset(BaseModel):
    """
    Password reset request schema
    """
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """
    Password reset confirmation schema
    """
    token: str
    new_password: str 