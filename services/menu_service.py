from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import date
from models.db_models import NutritionPlan, User, Meal
from core.prompts import MENU_DIARIO_PROMPT, MENU_SEMANAL_PROMPT, MENU_MENSUAL_PROMPT
from services.nutrition import (
    calcular_macros,
    get_meal_by_plan_and_id,
    get_user_plan_by_type,
    serialize_meal,
    get_total_intake_for_date,
    calculate_gap_for_day,
    generate_adjusted_menu,
    save_plan_adjustment
)
from services.groq_client import generate_menu_with_groq, generate_meal_with_groq

def generar_y_guardar_plan_ia(db: Session, current_user: User, tipo: str):
    # 1. Borrar plan existente si hay
    existing_plan = get_user_plan_by_type(db, current_user, tipo)
    if existing_plan:
        db.query(Meal).filter(Meal.plan_id == existing_plan.id).delete()
        db.delete(existing_plan)
        db.commit()

    # 2. Calcular calorías y macros
    calories, macros = calcular_macros(current_user)

    # 3. Elegir prompt según tipo
    prompt_map = {
        "diario": MENU_DIARIO_PROMPT,
        "semanal": MENU_SEMANAL_PROMPT,
        "mensual": MENU_MENSUAL_PROMPT
    }
    prompt = prompt_map.get(tipo, MENU_DIARIO_PROMPT)

    # 4. Generar comidas con IA
    comidas_generadas = generate_menu_with_groq(
        calories, macros,
        current_user.preferencias or [],
        current_user.restricciones or [],
        prompt
    )

    # 5. Crear nuevo plan
    new_plan = NutritionPlan(
        user_id=current_user.id,
        tipo=tipo,
        calorias=calories,
        macros=macros
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)

    # 6. Guardar comidas en DB
    saved_meals = []
    for comida in comidas_generadas:
        meal = Meal(
            plan_id=new_plan.id,
            dia=comida.get("dia", 1),
            turno=comida.get("turno", "comida"),
            nombre=comida.get("nombre", "Comida"),
            alimentos=comida.get("ingredientes", []),
            macros=comida.get("macros", {"carbohidratos_g":0,"proteinas_g":0,"grasas_g":0}),
            calorias=comida.get("calorias", 0),
            completed=False
        )
        db.add(meal)
        db.commit()
        db.refresh(meal)
        saved_meals.append(meal)

    # 7. Construir menús agrupados
    menu_full: Dict[str, Dict[str, List[dict]]] = {}
    menu_ids: Dict[str, Dict[str, List[int]]] = {}

    for meal in saved_meals:
        dia_str = str(meal.dia)
        turno = meal.turno

        if dia_str not in menu_full:
            menu_full[dia_str] = {"desayuno": [], "comida": [], "cena": []}
            menu_ids[dia_str] = {"desayuno": [], "comida": [], "cena": []}
        
        if turno not in menu_full[dia_str]:
            menu_full[dia_str][turno] = []
            menu_ids[dia_str][turno] = []

        menu_full[dia_str][turno].append(serialize_meal(meal))
        menu_ids[dia_str][turno].append(meal.id)

    new_plan.menu = menu_ids
    db.commit()
    
    new_plan.menu = menu_full
    return new_plan

def obtener_historial_menus(db: Session, current_user: User, tipo: Optional[str]):
    query = db.query(NutritionPlan).filter(NutritionPlan.user_id == current_user.id)
    if tipo:
        query = query.filter(NutritionPlan.tipo == tipo)
    
    planes = query.order_by(NutritionPlan.created_at.desc()).all()
    if not planes:
        return []

    resultado = []
    for plan in planes:
        meals = db.query(Meal).filter(Meal.plan_id == plan.id).all()
        menu_full: Dict[str, Dict[str, List[dict]]] = {}
        for meal in meals:
            dia_str = str(meal.dia)
            turno = meal.turno
            if dia_str not in menu_full:
                menu_full[dia_str] = {"desayuno": [], "almuerzo": [], "comida": [], "cena": []}
            if turno not in menu_full[dia_str]:
                menu_full[dia_str][turno] = []
            menu_full[dia_str][turno].append(serialize_meal(meal))

        resultado.append({
            "id": plan.id,
            "user_id": plan.user_id,
            "tipo": plan.tipo,
            "calorias": plan.calorias,
            "macros": plan.macros,
            "created_at": plan.created_at,
            "menu": menu_full
        })
    return resultado

def regenerar_comida_ia(db: Session, current_user: User, plan_id: int, meal_id: int):
    plan = db.query(NutritionPlan).filter(
        NutritionPlan.id == plan_id, NutritionPlan.user_id == current_user.id
    ).first()
    if not plan:
        raise ValueError("Plan no encontrado")

    meal = get_meal_by_plan_and_id(db, plan_id, meal_id)
    if not meal:
        raise ValueError("Comida no encontrada")

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

    meal.nombre = nueva_comida["nombre"]
    meal.alimentos = nueva_comida.get("ingredientes", [])
    meal.macros = nueva_comida["macros"]
    meal.calorias = nueva_comida["calorias"]
    db.commit()
    db.refresh(meal)
    return serialize_meal(meal)

def marcar_comida_completada(db: Session, current_user: User, meal_id: int, completed: bool):
    meal = db.query(Meal).join(NutritionPlan).filter(
        Meal.id == meal_id,
        NutritionPlan.user_id == current_user.id
    ).first()
    if not meal:
        raise ValueError("Comida no encontrada")

    meal.completed = completed
    db.commit()
    db.refresh(meal)
    return meal

def ajustar_plan_dia(db: Session, current_user: User, plan_id: int, f: Optional[date]):
    plan = db.query(NutritionPlan).filter(
        NutritionPlan.id == plan_id, NutritionPlan.user_id == current_user.id
    ).first()
    if not plan:
        raise ValueError("Plan no encontrado")

    consumed_cal, consumed_macros = get_total_intake_for_date(db, current_user, f)
    gap = calculate_gap_for_day(plan, consumed_cal, consumed_macros)
    adjusted_menu = generate_adjusted_menu(plan, gap, current_user)
    save_plan_adjustment(db, plan, adjusted_menu, f)
    
    return {"ok": True, "adjusted_menu": adjusted_menu}