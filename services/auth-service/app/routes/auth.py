from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import User
from app.schemas import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse
from app.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Autenticação Bancária"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    # 1. Checar se já existe correntista com mesmo CPF ou Email
    query = select(User).where((User.tax_id == payload.tax_id) | (User.email == payload.email))
    result = await db.execute(query)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="CPF ou e-mail já cadastrado no sistema bancário.")

    # 2. Criar novo correntista
    new_user = User(
        tax_id=payload.tax_id,
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. Buscar usuário
    query = select(User).where(User.tax_id == payload.tax_id)
    result = await db.execute(query)
    user = result.scalars().first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="CPF ou senha inválidos.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta bancária inativa.")

    # 2. Gerar JWT Token
    token = create_access_token(data={"sub": str(user.id), "tax_id": user.tax_id, "name": user.full_name})
    return TokenResponse(access_token=token, expires_in=3600)
