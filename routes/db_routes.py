from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from models.db_models import User, NutritionPlan

router = APIRouter()

# 🔹 Crear usuario básico
@router.post("/users")
def create_user(nombre: str, edad: int, genero: str, db: Session = Depends(get_db)):
    user = User(nombre=nombre, edad=edad, genero=genero)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# 🔹 Actualizar perfil completo
@router.patch("/users/{user_id}")
def update_user_profile(
    user_id: int,
    peso: float = None,
    altura: float = None,
    nivel_actividad: str = None,
    objetivo: str = None,
    preferencias: list[str] = None,
    restricciones: list[str] = None,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if peso is not None:
        user.peso = peso
    if altura is not None:
        user.altura = altura
    if nivel_actividad is not None:
        user.nivel_actividad = nivel_actividad
    if objetivo is not None:
        user.objetivo = objetivo
    if preferencias is not None:
        user.preferencias = preferencias
    if restricciones is not None:
        user.restricciones = restricciones

    db.commit()
    db.refresh(user)
    return user

# 🔹 Listar usuarios
@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

# 🔹 Guardar plan nutricional
@router.post("/plans")
def save_plan(user_id: int, tipo: str, calorias: float, macros: dict, menu: dict, db: Session = Depends(get_db)):
    plan = NutritionPlan(user_id=user_id, tipo=tipo, calorias=calorias, macros=macros, menu=menu)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

# 🔹 Listar planes de un usuario
@router.get("/plans/{user_id}")
def get_user_plans(user_id: int, db: Session = Depends(get_db)):
    return db.query(NutritionPlan).filter(NutritionPlan.user_id == user_id).all()
