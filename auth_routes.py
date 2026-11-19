"""
用户认证API路由
Authentication API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from database import get_db
from models import User
from auth import (
    create_access_token,
    authenticate_user,
    get_current_user,
    get_password_hash,
    require_role
)
from crud import (
    create_user,
    get_user_by_username,
    get_user_by_email,
    update_user_last_login
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


# ==================== Pydantic Models ====================

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
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
    created_at: Optional[str]
    last_login: Optional[str]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# ==================== API Endpoints ====================

@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    用户注册
    """
    # 检查用户名是否已存在
    existing_user = get_user_by_username(db, request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册"
        )
    
    # 检查邮箱是否已存在
    existing_email = get_user_by_email(db, request.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 验证角色
    if request.role not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的角色类型，只能选择教师或管理员"
        )
    
    # 创建用户
    try:
        user = create_user(db, request.username, request.email, request.password, request.role)
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录
    """
    # 验证用户凭据
    user = authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 更新最后登录时间
    update_user_last_login(db, user.id)
    
    # 生成JWT Token
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at.isoformat() if user.created_at else None,
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户信息
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
        last_login=current_user.last_login.isoformat() if current_user.last_login else None
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    用户登出（前端删除Token即可）
    """
    return JSONResponse({"message": "登出成功"})


@router.get("/check-username/{username}")
async def check_username(username: str, db: Session = Depends(get_db)):
    """
    检查用户名是否可用
    """
    user = get_user_by_username(db, username)
    return JSONResponse({"available": user is None})


@router.get("/check-email/{email}")
async def check_email(email: str, db: Session = Depends(get_db)):
    """
    检查邮箱是否可用
    """
    user = get_user_by_email(db, email)
    return JSONResponse({"available": user is None})
