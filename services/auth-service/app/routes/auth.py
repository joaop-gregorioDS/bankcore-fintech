from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    DirectoryLookupResponse,
)
from app.security import hash_password, verify_password, create_access_token, get_current_user
from app.seed import normalize_tax_id

router = APIRouter(prefix="/auth", tags=["Autenticação Bancária"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    tax_id = normalize_tax_id(payload.tax_id)
    query = select(User).where((User.tax_id == tax_id) | (User.email == payload.email))
    result = await db.execute(query)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="CPF ou e-mail já cadastrado no sistema bancário.")

    new_user = User(
        tax_id=tax_id,
        full_name=payload.full_name.strip(),
        email=payload.email,
        hashed_password=hash_password(payload.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    tax_id = normalize_tax_id(payload.tax_id)
    query = select(User).where(User.tax_id == tax_id)
    result = await db.execute(query)
    user = result.scalars().first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="CPF ou senha inválidos.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta bancária inativa.")

    token = create_access_token(data={"sub": str(user.id), "tax_id": user.tax_id, "name": user.full_name})
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.id == UUID(current_user["sub"]))
    result = await db.execute(query)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Correntista não encontrado.")
    return user


@router.get("/directory/{tax_id}", response_model=DirectoryLookupResponse)
async def lookup_directory(
    tax_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    normalized = normalize_tax_id(tax_id)
    if len(normalized) < 11:
        raise HTTPException(status_code=400, detail="Chave Pix (CPF/CNPJ) inválida.")

    query = select(User).where(User.tax_id == normalized, User.is_active.is_(True))
    result = await db.execute(query)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Chave Pix (CPF) não encontrada no banco.")

    return DirectoryLookupResponse(user_id=user.id, tax_id=user.tax_id, full_name=user.full_name)
