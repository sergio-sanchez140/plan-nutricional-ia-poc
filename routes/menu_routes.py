from fastapi import APIRouter, Depends, HTTPException
from models.db_models import NutritionPlan, User
from models.plan_schemas import MenuTipoRequest, NutritionPlanCreate, NutritionPlanRead
from sqlalchemy.orm import Session
from typing import List
from db.database import get_db
from utils.auth_utils import get_current_user
from services.nutrition import calcular_macros
from services.groq_client import generate_menu_with_groq
from core.prompts import MENU_DIARIO_PROMPT, MENU_SEMANAL_PROMPT, MENU_MENSUAL_PROMPT
from utils.validation_utils import validar_datos_usuario

router = APIRouter()

@router.post("/menus/generate", response_model=NutritionPlanRead)
def generar_menu_ia(
    menu_request: MenuTipoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validación obligatoria
    validar_datos_usuario(current_user)
    
    # 🔹 Usamos los datos del usuario desde el token
    user_data = {
        "edad": current_user.edad,
        "peso": current_user.peso,
        "altura": current_user.altura,
        "nivel_actividad": current_user.nivel_actividad,
        "objetivo": current_user.objetivo,
        "preferencias": current_user.preferencias or [],
        "restricciones": current_user.restricciones or []
    }

    # 🔹 Calculamos calorías y macros
    calories, macros = calcular_macros(current_user)
    
    # 🔹 Selección del prompt según tipo
    prompt_map = {
        "diario": MENU_DIARIO_PROMPT,
        "semanal": MENU_SEMANAL_PROMPT,
        "mensual": MENU_MENSUAL_PROMPT
    }
    prompt = prompt_map[menu_request.tipo]

    # 🔹 Generamos el menú con IA
    menu = generate_menu_with_groq(
        calories, macros,
        user_data["preferencias"],
        user_data["restricciones"],
        prompt
    )

    # 🔹 Guardamos el plan en la base de datos
    new_plan = NutritionPlan(
        user_id=current_user.id,
        tipo=menu_request.tipo,
        calorias=calories,
        macros=macros,
        menu=menu
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)

    return new_plan

# 🔹 Obtener menús del usuario
@router.get("/menus", response_model=List[NutritionPlanRead])
def obtener_menus(
    tipo: str = None,  # diario/semanal/mensual
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(NutritionPlan).filter(NutritionPlan.user_id == current_user.id)
    if tipo:
        query = query.filter(NutritionPlan.tipo == tipo)
    return query.order_by(NutritionPlan.created_at.desc()).all()