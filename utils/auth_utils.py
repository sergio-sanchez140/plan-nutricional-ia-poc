# utils/auth_utils.py
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from db.database import get_db
from models.db_models import User, TokenBlacklist
from core.config import settings

# 🔹 Hash de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# 🔹 JWT
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # ✅ AHORA USA EL .ENV (settings)
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    # ✅ AHORA USA EL .ENV (settings)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str):
    try:
        # ✅ AHORA USA EL .ENV (settings)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None

# 🔹 OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    # 🔹 Revisar si el token está en blacklist
    blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.token == token).first()
    if blacklisted:
        raise HTTPException(status_code=401, detail="Token revocado")

    user = db.query(User).filter(User.email == payload.get("sub")).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user