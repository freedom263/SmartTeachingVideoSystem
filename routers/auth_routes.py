"""
用户认证 API 路由 (Authentication API Routes)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database.connection import get_db
from database.models import User
import database.crud as crud
from auth import (
    create_access_token,
    authenticate_user,
    get_current_user,
    require_role
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = "teacher"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: Optional[str] = None
    last_login: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    if crud.get_user_by_username(db, req.username):
        raise HTTPException(status_code=400, detail="用户名已被使用")
    if crud.get_user_by_email(db, req.email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = crud.create_user(
        db=db,
        username=req.username,
        email=req.email,
        password=req.password,
        role=req.role or "student"
    )
    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user.to_dict()}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录获取 JWT"""
    user = authenticate_user(db, req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    crud.update_user_last_login(db, user.id)
    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user.to_dict()}


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user.to_dict()
