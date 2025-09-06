from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from db.database import get_db
from models.db_models import User
from models.user_data import UserCreate, UserUpdate, UserLogin
from models.db_models import NutritionPlan, User
from models.plan_schemas import NutritionPlanCreate
from utils.auth_utils import create_access_token, get_current_user, verify_password

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# 🔹 Crear usuario
@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Pydantic ya validó `nombre` y `password` antes de entrar aquí
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    db_user = User(
        nombre=user.nombre,
        email=user.email,
        hashed_password=hash_password(user.password)  # SQLAlchemy necesita este campo
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"id": db_user.id, "nombre": db_user.nombre, "email": db_user.email}

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
        "peso": current_user.peso
    }