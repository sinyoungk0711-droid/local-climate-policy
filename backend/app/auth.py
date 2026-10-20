import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from pymysql.err import IntegrityError, MySQLError

from .climate_data import connect_db

router = APIRouter(prefix="/api/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)
TOKEN_TTL_SECONDS = 60 * 60 * 12


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    display_name: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("올바른 이메일 주소를 입력하세요.")
        return value

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("닉네임은 2자 이상 입력하세요.")
        return value


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


def _secret() -> bytes:
    value = os.getenv("AUTH_SECRET_KEY", "")
    if len(value) < 32:
        raise HTTPException(status_code=503, detail="AUTH_SECRET_KEY에 32자 이상의 임의 비밀키를 설정하세요.")
    return value.encode("utf-8")


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return base64.urlsafe_b64encode(salt).decode().rstrip("=") + "$" + base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_text, digest_text = stored.split("$", 1)
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(digest_text + "=" * (-len(digest_text) % 4))
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _create_token(user_id: int, email: str) -> str:
    secret = _secret()
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": str(user_id), "email": email, "iat": now, "exp": now + TOKEN_TTL_SECONDS}, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = _b64(hmac.new(secret, signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def _decode_token(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        signing_input = f"{header}.{payload}".encode()
        expected = _b64(hmac.new(_secret(), signing_input, hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        decoded_header = json.loads(base64.urlsafe_b64decode(header + "=" * (-len(header) % 4)))
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if decoded_header.get("alg") != "HS256" or int(claims.get("exp", 0)) <= int(time.time()):
            raise ValueError("expired")
        return claims
    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="로그인 정보가 만료되었거나 유효하지 않습니다. 다시 로그인하세요.")


def current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    claims = _decode_token(credentials.credentials)
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, email, display_name, created_at FROM users WHERE user_id=%s AND is_active=1", (int(claims["sub"]),))
            user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="사용자 계정을 찾을 수 없습니다.")
        if user.get("created_at"):
            user["created_at"] = user["created_at"].isoformat()
        return user
    finally:
        conn.close()


@router.post("/register", status_code=201)
def register(payload: RegisterRequest):
    _secret()
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE email=%s LIMIT 1", (payload.email,))
            if cur.fetchone():
                raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다. 로그인해 주세요.")
            password_hash = _hash_password(payload.password)
            cur.execute("INSERT INTO users (email, display_name, password_hash) VALUES (%s,%s,%s)",
                        (payload.email, payload.display_name, password_hash))
            user_id = cur.lastrowid
        conn.commit()
        return {"access_token": _create_token(user_id, payload.email), "token_type": "bearer",
                "expires_in": TOKEN_TTL_SECONDS,
                "user": {"user_id": user_id, "email": payload.email, "display_name": payload.display_name}}
    except HTTPException:
        conn.rollback()
        raise
    except IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다. 로그인해 주세요.")
    except MySQLError as exc:
        conn.rollback()
        raise HTTPException(status_code=503, detail="회원가입 DB 오류: " + str(exc)[:180])
    finally:
        conn.close()


@router.post("/login")
def login(payload: LoginRequest):
    _secret()
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, email, display_name, password_hash FROM users WHERE email=%s AND is_active=1 LIMIT 1", (payload.email,))
            user = cur.fetchone()
        if not user or not _verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
        return {"access_token": _create_token(user["user_id"], user["email"]), "token_type": "bearer",
                "expires_in": TOKEN_TTL_SECONDS,
                "user": {"user_id": user["user_id"], "email": user["email"], "display_name": user["display_name"]}}
    finally:
        conn.close()


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {"user": user}


@router.post("/logout")
def logout(user: dict = Depends(current_user)):
    # Bearer tokens are stateless; the browser must discard the token on logout.
    return {"ok": True, "message": "브라우저에서 로그인 토큰을 삭제하세요."}
