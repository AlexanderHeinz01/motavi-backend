from typing import Literal, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    company: Optional[str] = None
    # "berater" may review process steps (expert view); registration needs the setup key
    role: Literal["user", "berater"] = "user"


class UserPublic(BaseModel):
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    role: str = "user"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
