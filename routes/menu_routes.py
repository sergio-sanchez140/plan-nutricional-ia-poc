from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

# Base de datos y Auth
from db.database import get_db
from utils.auth_utils import get_current_user
from models.db_models import User
from models.plan_schemas import MenuTipoRequest, NutritionPlanRead, MealRead, IntakeSchema

# Servicios delegados (¡Aquí está la magia de la refactorización!)
from services.groq_client import analyze_image_with_groq
from services.intake_service import procesar_y_guardar_ingesta, obtener_ingestas_hoy
from services.menu_service import (
    generar_y_guardar_plan_ia, 
    obtener_historial_menus, 
    regenerar_comida_ia, 
    marcar_comida_completada,
    ajustar_plan_dia
)
from utils.validation_utils import validar_datos_usuario

router = APIRouter()

# ==========================================
# 👁️ VISIÓN IA
# ==========================================

@router.post("/vision/analyze")
async def analyze_food_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    content_type = file.content_type
    is_image = content_type.startswith("image/") or file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.jfif'))
    
    if not is_image:
        raise HTTPException(status_code=400, detail=f"Archivo inválido. Tipo recibido: {content_type}")

    try:
        safe_mime_type = content_type if content_type.startswith("image/") else "image/jpeg"
        return analyze_image_with_groq(await file.read(), safe_mime_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analizando imagen: {str(e)}")

# ==========================================
# 🍽️ INGESTAS (INTAKES)
# ==========================================

@router.get("/intakes/today")
def get_today_intake(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return obtener_ingestas_hoy(db, current_user)

@router.post("/intakes")
def create_intake(data: IntakeSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not data.nombre_plato and not data.texto:
        raise HTTPException(status_code=400, detail="Debes enviar 'texto' o 'nombre_plato'")
    
    return procesar_y_guardar_ingesta(db, current_user, data)

# ==========================================
# 📅 MENÚS Y PLANES
# ==========================================

@router.post("/menus/generate", response_model=NutritionPlanRead)
def generar_menu_ia(menu_request: MenuTipoRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    validar_datos_usuario(current_user)
    return generar_y_guardar_plan_ia(db, current_user, menu_request.tipo)

@router.get("/menus", response_model=List[NutritionPlanRead])
def obtener_menus(tipo: Optional[str] = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return obtener_historial_menus(db, current_user, tipo)

@router.post("/menus/{plan_id}/replace-meal/{meal_id}")
def sustituir_comida(plan_id: int, meal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return regenerar_comida_ia(db, current_user, plan_id, meal_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/meals/{meal_id}/toggle", response_model=MealRead)
def toggle_meal_completed(meal_id: int, completed: bool, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return marcar_comida_completada(db, current_user, meal_id, completed)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/menus/{plan_id}/adjust")
def adjust_plan_for_date(plan_id: int, fecha: Optional[str] = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        f = date.fromisoformat(fecha) if fecha else None
        return ajustar_plan_dia(db, current_user, plan_id, f)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))