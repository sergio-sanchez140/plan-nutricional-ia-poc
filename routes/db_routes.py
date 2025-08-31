from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from models.db_models import User
from models.user_data import UserCreate, UserUpdate
from models.db_models import NutritionPlan, User
from models.plan_schemas import NutritionPlanCreate

router = APIRouter()

# 🔹 Crear usuario
@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    db_user = User(nombre=user.nombre, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

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