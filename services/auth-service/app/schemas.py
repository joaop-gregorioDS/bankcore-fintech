from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID

class UserRegisterRequest(BaseModel):
    tax_id: str = Field(..., description="CPF ou CNPJ (somente números)", min_length=11, max_length=14)
    full_name: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, description="Senha forte de pelo menos 8 dígitos")

class UserLoginRequest(BaseModel):
    tax_id: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class UserResponse(BaseModel):
    id: UUID
    tax_id: str
    full_name: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class DirectoryLookupResponse(BaseModel):
    user_id: UUID
    tax_id: str
    full_name: str
