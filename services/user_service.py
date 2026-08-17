import cloudinary
import cloudinary.uploader
from fastapi import UploadFile
from sqlalchemy.orm import Session

from core.config import settings
from models.db_models import User, NutritionPlan
from models.user_data import UserUpdate
from models.plan_schemas import NutritionPlanCreate

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

def subir_avatar(db: Session, current_user: User, file: UploadFile) -> str:
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raise ValueError("Formato de imagen no soportado")
        
    result = cloudinary.uploader.upload(file.file)
    secure_url = result.get("secure_url")
    
    current_user.avatar_url = secure_url
    db.commit()
    return secure_url

def actualizar_perfil(db: Session, email: str, data: UserUpdate) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError("Usuario no encontrado")
    
    for key, value in data.dict(exclude_unset=True).items():
        setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user

def crear_plan_nutricional(db: Session, plan: NutritionPlanCreate) -> NutritionPlan:
    user = db.query(User).filter(User.id == plan.user_id).first()
    if not user:
        raise ValueError("Usuario no encontrado")

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