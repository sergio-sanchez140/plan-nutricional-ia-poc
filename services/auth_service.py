import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from core.config import settings
from models.db_models import User, TokenBlacklist
from models.user_data import UserCreate, UserLogin, GoogleToken
from utils.auth_utils import create_access_token, verify_password, hash_password

def registrar_usuario(db: Session, user: UserCreate) -> dict:
    if db.query(User).filter(User.email == user.email).first():
        raise ValueError("El email ya está registrado")

    db_user = User(
        nombre=user.nombre,
        email=user.email,
        hashed_password=hash_password(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token = create_access_token(data={"sub": db_user.email})
    return {
        "user": {"id": db_user.id, "nombre": db_user.nombre, "email": db_user.email},
        "access_token": access_token,
        "token_type": "bearer"
    }

def autenticar_usuario(db: Session, user: UserLogin) -> dict:
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise ValueError("Email o contraseña incorrectos")
    
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

def autenticar_google(db: Session, token_data: GoogleToken) -> dict:
    email = None
    nombre = "Usuario Google"

    if token_data.id_token:
        idinfo = id_token.verify_oauth2_token(token_data.id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
        email = idinfo['email']
        nombre = idinfo.get('name', 'Usuario Google')
    elif token_data.access_token:
        response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data.access_token}"}
        )
        if response.status_code != 200:
            raise ValueError("Access token inválido o caducado")
        user_info = response.json()
        email = user_info['email']
        nombre = user_info.get('name', 'Usuario Google')
    else:
        raise ValueError("Se requiere id_token o access_token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=hash_password(f"google_dummy_{email}_2026"),
            nombre=nombre
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "nombre": user.nombre
    }

def cerrar_sesion(db: Session, token: str):
    db.add(TokenBlacklist(token=token))
    db.commit()
    return {"message": "Sesión cerrada correctamente"}