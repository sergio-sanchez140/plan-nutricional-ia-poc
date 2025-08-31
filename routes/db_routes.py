from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from models.db_models import User
from models.user_data import UserCreate, UserUpdate

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
