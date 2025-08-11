from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.mongo_chat_store import get_mongo_store
from app.config.settings import settings


router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    username: str = Field(...)
    password: str = Field(..., min_length=6)


class SignupResponse(BaseModel):
    user_id: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str


@router.post("/signup", response_model=SignupResponse)
async def signup(request: SignupRequest):
    store = get_mongo_store()
    try:
        user = await store.create_user(request.username, request.password)
        return SignupResponse(user_id=user["user_id"], username=user["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    store = get_mongo_store()
    user = await store.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = store.create_access_token(
        data={"sub": user["user_id"], "username": user["username"]},
        expires_minutes=settings.access_token_expires_minutes,
    )
    return TokenResponse(access_token=token, user_id=user["user_id"], username=user["username"])


