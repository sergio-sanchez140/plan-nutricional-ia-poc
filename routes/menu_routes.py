from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from fastapi import Body, Query

from models.db_models import NutritionPlan, User, Meal
from models.plan_schemas import MenuTipoRequest, NutritionPlanRead, MealRead
from db.database import get_db
from utils.auth_utils import get_current_user
from services.nutrition import (
    calcular_macros,
    get_meal_by_plan_and_id,
    get_user_plan_by_type,
    serialize_meal,
    record_user_intake,
    get_total_intake_for_date,
    calculate_gap_for_day,
    generate_adjusted_menu,
    save_plan_adjustment
)
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
    # Validar datos del usuario
    validar_datos_usuario(current_user)

    # 🔹 Borrar plan existente si hay
    existing_plan = get_user_plan_by_type(db, current_user, menu_request.tipo)
    if existing_plan:
        db.query(Meal).filter(Meal.plan_id == existing_plan.id).delete()
        db.delete(existing_plan)
        db.commit()

    # 🔹 Calcular calorías y macros
    calories, macros = calcular_macros(current_user)

    # 🔹 Elegir prompt según tipo
    prompt_map = {
        "diario": MENU_DIARIO_PROMPT,
        "semanal": MENU_SEMANAL_PROMPT,
        "mensual": MENU_MENSUAL_PROMPT
    }
    prompt = prompt_map[menu_request.tipo]

    # 🔹 Generar comidas con IA
    comidas_generadas = generate_menu_with_groq(
        calories, macros,
        current_user.preferencias or [],
        current_user.restricciones or [],
        prompt
    )

    # 🔹 Crear nuevo plan
    new_plan = NutritionPlan(
        user_id=current_user.id,
        tipo=menu_request.tipo,
        calorias=calories,
        macros=macros
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)

    print(comidas_generadas)

    # 🔹 Guardar comidas y construir mapping por turno
    saved_meals: List[tuple[Meal, str]] = []
    for comida in comidas_generadas:
        meal = Meal(
            plan_id=new_plan.id,
            nombre=comida.get("nombre", "Comida"),
            alimentos=comida.get("ingredientes", []),
            macros=comida.get("macros", {"carbohidratos_g":0,"proteinas_g":0,"grasas_g":0}),
            calorias=comida.get("calorias", 0),
            completed=False
        )
        print(comida.get("turno"))
        db.add(meal)
        db.commit()
        db.refresh(meal)
        saved_meals.append((meal, comida.get("turno", "comida")))

    # 🔹 Construir menú completo para la respuesta
    menu_full: Dict[str, List[dict]] = {"desayuno": [], "comida": [], "cena": []}
    menu_ids: Dict[str, List[int]] = {"desayuno": [], "comida": [], "cena": []}
    for meal, turno in saved_meals:
        menu_full[turno].append(serialize_meal(meal))
        menu_ids[turno].append(meal.id)

    # 🔹 Guardar mapping de IDs en plan
    new_plan.menu = menu_ids
    db.commit()
    db.refresh(new_plan)

    print(menu_ids)

    # 🔹 Adjuntar menú completo para la respuesta
    new_plan.menu = menu_full
    return new_plan

@router.get("/menus", response_model=List[NutritionPlanRead])
def obtener_menus(
    tipo: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if tipo:
        # 🔹 Buscar el plan del usuario según tipo
        plan = get_user_plan_by_type(db, current_user, tipo)
        if not plan:
            return []

        # 🔹 Obtener lo consumido hoy
        consumed_cal, consumed_macros = get_total_intake_for_date(db, current_user)

        # 🔹 Calcular diferencias
        gap = calculate_gap_for_day(plan, consumed_cal, consumed_macros)

        # 🔹 (Opcional) Generar menú ajustado según gap
        # Aquí podemos llamar a un motor IA o a un fallback.
        adjusted_menu = generate_adjusted_menu(plan, gap, current_user)

        # 🔹 Guardar ajuste en DB (para persistencia del día)
        save_plan_adjustment(db, plan, adjusted_menu)

        return [{
            **plan.__dict__,
            "menu": adjusted_menu
        }]

    # 🔹 Caso sin filtro: devolver todos los planes del usuario
    query = db.query(NutritionPlan).filter(NutritionPlan.user_id == current_user.id)
    return query.order_by(NutritionPlan.created_at.desc()).all()

@router.post("/menus/{plan_id}/replace-meal/{meal_id}")
def sustituir_comida(
    plan_id: int,
    meal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 🔹 Recuperar plan
    plan = db.query(NutritionPlan).filter(
        NutritionPlan.id == plan_id,
        NutritionPlan.user_id == current_user.id
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    # 🔹 Recuperar comida
    meal = get_meal_by_plan_and_id(db, plan_id, meal_id)

    # 🔹 Generar nueva comida con la IA
    nueva_comida = generate_meal_with_groq(
        {
            "nombre": meal.nombre,
            "ingredientes": meal.alimentos,
            "macros": meal.macros,
            "calorias": meal.calorias
        },
        current_user.preferencias or [],
        current_user.restricciones or []
    )

    # 🔹 Actualizar la comida en la base de datos
    meal.nombre = nueva_comida["nombre"]
    meal.alimentos = nueva_comida.get("ingredientes", [])
    meal.macros = nueva_comida["macros"]
    meal.calorias = nueva_comida["calorias"]
    db.commit()
    db.refresh(meal)

    # 🔹 Retornar solo la comida en el formato requerido
    return serialize_meal(meal)

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

@router.post("/intakes")
def create_intake(
    alimentos: List[Dict[str,Any]] = Body(..., example=[{"nombre":"Big Mac","cantidad_g":200}]),
    calorias: int = Body(..., example=563),
    macros: Dict[str,int] = Body(..., example={"carbohidratos_g":45,"proteinas_g":25,"grasas_g":33}),
    fecha: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Registrar una ingesta del usuario (comida real).
    fecha: ISO YYYY-MM-DD opcional (default hoy)
    """
    f = date.fromisoformat(fecha) if fecha else None
    try:
        intake = record_user_intake(db, current_user, alimentos, calorias, macros, f)
        return {"ok": True, "intake_id": intake.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/menus/{plan_id}/adjust")
def adjust_plan_for_date(
    plan_id: int,
    fecha: Optional[str] = Query(None, description="YYYY-MM-DD (default hoy)"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Forzar recálculo del plan para la fecha.
    """

    f = date.fromisoformat(fecha) if fecha else None

    plan = db.query(NutritionPlan).filter(
        NutritionPlan.id == plan_id,
        NutritionPlan.user_id == current_user.id
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    try:
        consumed_cal, consumed_macros = get_total_intake_for_date(
            db,
            current_user,
            f
        )

        gap = calculate_gap_for_day(
            plan,
            consumed_cal,
            consumed_macros
        )

        adjusted_menu = generate_adjusted_menu(
            plan,
            gap,
            current_user
        )

        save_plan_adjustment(
            db,
            plan,
            adjusted_menu,
            f
        )

        return {
            "ok": True,
            "adjusted_menu": adjusted_menu
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
