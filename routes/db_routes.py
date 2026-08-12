from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from core.config import settings
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from db.database import get_db
from models.db_models import TokenBlacklist, User
from models.user_data import UserCreate, UserUpdate, UserLogin
from models.db_models import NutritionPlan, User
from models.plan_schemas import NutritionPlanCreate
from utils.auth_utils import create_access_token, get_current_user, verify_password, oauth2_scheme

class GoogleToken(BaseModel):
    token: str

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# 🔹 Crear usuario
@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    db_user = User(
        nombre=user.nombre,
        email=user.email,
        hashed_password=hash_password(user.password)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # 🔥 AUTO LOGIN
    access_token = create_access_token(data={"sub": db_user.email})

    return {
        "user": {
            "id": db_user.id,
            "nombre": db_user.nombre,
            "email": db_user.email
        },
        "access_token": access_token,
        "token_type": "bearer"
    }

# 🔹 Actualizar usuario
@router.put("/users/{email}")
def update_user(email: str, data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    for key, value in data.dict(exclude_unset=True).items():
        setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user

# 🔹 Listar usuarios
@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()

# Guardar plan nutricional
@router.post("/plans")
def save_plan(plan: NutritionPlanCreate, db: Session = Depends(get_db)):
    # Verificar que el usuario exista
    user = db.query(User).filter(User.id == plan.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Crear plan
    new_plan = NutritionPlan(
        user_id=plan.user_id,
        tipo=plan.tipo,
        calorias=plan.calorias,
        macros=plan.macros,
        menu=plan.menu
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    return new_plan

# Listar planes de un usuario
@router.get("/plans/{user_id}")
def get_user_plans(user_id: int, db: Session = Depends(get_db)):
    return db.query(NutritionPlan).filter(NutritionPlan.user_id == user_id).all()

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Email o contraseña incorrectos")
    
    # Generar token JWT
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    return {
        "nombre": current_user.nombre,
        "email": current_user.email,
        "edad": current_user.edad,
        "genero": current_user.genero,
        "peso": current_user.peso,
        "altura": current_user.altura,
        "nivel_actividad": current_user.nivel_actividad,
        "objetivo": current_user.objetivo,
        "preferencias": current_user.preferencias,
        "restricciones": current_user.restricciones
    }

@router.post("/logout")
def logout(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Guardar token en blacklist
    db.add(TokenBlacklist(token=token))
    db.commit()
    return {"message": "Sesión cerrada correctamente"}

@router.post("/login/google")
def google_login(token_data: GoogleToken, db: Session = Depends(get_db)):
    try:
        # 1. Validar ticket con Google
        idinfo = id_token.verify_oauth2_token(
            token_data.token, 
            google_requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        # 2. Extraer datos del perfil de Google
        email = idinfo['email']
        nombre = idinfo.get('name', 'Usuario Google')
        
        # 3. Buscar si el usuario ya existe en nuestra base de datos
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # 4. Si no existe, lo registramos automáticamente.
            # Usamos tu función hash_password con una contraseña imposible.
            user = User(
                email=email,
                hashed_password=hash_password(f"google_dummy_{email}_2026"),
                nombre=nombre
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 5. Generar nuestro token JWT (igual que en tu /login normal)
        access_token = create_access_token(data={"sub": user.email})
        
        # 6. Devolver respuesta a Flutter
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
            "nombre": user.nombre
        }

    except ValueError:
        # Si el token no es válido o ha caducado
        raise HTTPException(
            status_code=401,
            detail="El token de Google es inválido o ha caducado",
            headers={"WWW-Authenticate": "Bearer"},
        )