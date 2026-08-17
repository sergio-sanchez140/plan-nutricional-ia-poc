from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session

from db.database import get_db
from models.db_models import User, NutritionPlan
from models.user_data import UserCreate, UserUpdate, UserLogin, GoogleToken
from models.plan_schemas import NutritionPlanCreate
from utils.auth_utils import get_current_user, oauth2_scheme

from services.auth_service import registrar_usuario, autenticar_usuario, autenticar_google, cerrar_sesion
from services.user_service import subir_avatar, actualizar_perfil, crear_plan_nutricional

router = APIRouter()

# ==========================================
# 🔐 AUTENTICACIÓN
# ==========================================

@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        return registrar_usuario(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        return autenticar_usuario(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login/google")
def google_login(token_data: GoogleToken, db: Session = Depends(get_db)):
    try:
        return autenticar_google(db, token_data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e), headers={"WWW-Authenticate": "Bearer"})

@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return cerrar_sesion(db, token)

# ==========================================
# 👤 USUARIOS Y PERFIL
# ==========================================

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
        "restricciones": current_user.restricciones,
        "avatar_url": current_user.avatar_url
    }

@router.post("/users/me/avatar")
def upload_avatar(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        secure_url = subir_avatar(db, current_user, file)
        return {"avatar_url": secure_url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error subiendo a la nube: {str(e)}")

@router.put("/users/{email}")
def update_user(email: str, data: UserUpdate, db: Session = Depends(get_db)):
    try:
        return actualizar_perfil(db, email, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()

# ==========================================
# 📅 PLANES NUTRICIONALES
# ==========================================

@router.post("/plans")
def save_plan(plan: NutritionPlanCreate, db: Session = Depends(get_db)):
    try:
        return crear_plan_nutricional(db, plan)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/plans/{user_id}")
def get_user_plans(user_id: int, db: Session = Depends(get_db)):
    return db.query(NutritionPlan).filter(NutritionPlan.user_id == user_id).all()