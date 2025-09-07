from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from models.db_models import NutritionPlan, User, Meal
from models.plan_schemas import MenuTipoRequest, NutritionPlanRead, MealRead
from db.database import get_db
from utils.auth_utils import get_current_user
from services.nutrition import calcular_macros
from services.groq_client import generate_meal_with_groq, generate_menu_with_groq
from core.prompts import MENU_DIARIO_PROMPT, MENU_SEMANAL_PROMPT, MENU_MENSUAL_PROMPT
from utils.validation_utils import validar_datos_usuario

router = APIRouter()


@router.post("/menus/generate", response_model=NutritionPlanRead)
def generar_menu_ia(
    menu_request: MenuTipoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    validar_datos_usuario(current_user)

    user_data = {
        "edad": current_user.edad,
        "peso": current_user.peso,
        "altura": current_user.altura,
        "nivel_actividad": current_user.nivel_actividad,
        "objetivo": current_user.objetivo,
        "preferencias": current_user.preferencias or [],
        "restricciones": current_user.restricciones or []
    }

    calories, macros = calcular_macros(current_user)
    prompt_map = {
        "diario": MENU_DIARIO_PROMPT,
        "semanal": MENU_SEMANAL_PROMPT,
        "mensual": MENU_MENSUAL_PROMPT
    }
    prompt = prompt_map[menu_request.tipo]

    comidas_generadas = generate_menu_with_groq(
        calories, macros,
        user_data["preferencias"],
        user_data["restricciones"],
        prompt
    )

    new_plan = NutritionPlan(
        user_id=current_user.id,
        tipo=menu_request.tipo,
        calorias=calories,
        macros=macros
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)

    # Guardar comidas y construir mapping turno -> meal_ids
    menu_mapping: Dict[str, List[int]] = {}
    for comida in comidas_generadas:
        turno = comida.get("turno", "comida")
        meal = Meal(
            plan_id=new_plan.id,
            nombre=comida["nombre"],
            alimentos=comida.get("ingredientes", []),
            macros=comida.get("macros", {"carbohidratos_g":0,"proteinas_g":0,"grasas_g":0}),
            calorias=comida.get("calorias", 0),
            completed=False
        )
        db.add(meal)
        db.commit()
        db.refresh(meal)

        if turno not in menu_mapping:
            menu_mapping[turno] = []
        menu_mapping[turno].append(meal.id)

    # Guardar mapping en plan
    new_plan.menu = menu_mapping
    db.commit()
    db.refresh(new_plan)
    return new_plan


@router.get("/menus", response_model=List[NutritionPlanRead])
def obtener_menus(
    tipo: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(NutritionPlan).filter(NutritionPlan.user_id == current_user.id)
    if tipo:
        query = query.filter(NutritionPlan.tipo == tipo)
    return query.order_by(NutritionPlan.created_at.desc()).all()


@router.post("/menus/{plan_id}/replace-meal")
def sustituir_comida(
    plan_id: int,
    meal_info: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    plan = db.query(NutritionPlan).filter(
        NutritionPlan.id == plan_id,
        NutritionPlan.user_id == current_user.id
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    nueva_comida = generate_meal_with_groq(
        meal_info,
        current_user.preferencias or [],
        current_user.restricciones or []
    )

    meal = db.query(Meal).filter(
        Meal.plan_id == plan.id,
        Meal.nombre == meal_info["nombre"]
    ).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Comida no encontrada")

    meal.nombre = nueva_comida["nombre"]
    meal.macros = nueva_comida["macros"]
    meal.calorias = nueva_comida["calorias"]
    db.commit()
    db.refresh(meal)

    return {
        "mensaje": "Comida sustituida correctamente",
        "nueva_comida": meal
    }


@router.patch("/meals/{meal_id}/toggle", response_model=MealRead)
def toggle_meal_completed(
    meal_id: int,
    completed: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meal = db.query(Meal).join(NutritionPlan).filter(
        Meal.id == meal_id,
        NutritionPlan.user_id == current_user.id
    ).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Comida no encontrada")

    meal.completed = completed
    db.commit()
    db.refresh(meal)
    return meal