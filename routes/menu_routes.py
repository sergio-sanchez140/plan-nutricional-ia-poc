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
from services.groq_client import analyze_intake_with_groq

router = APIRouter()

@router.get("/intakes/today")
def get_today_intake(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Devuelve las calorías y macros totales consumidos en el día actual.
    """
    from datetime import date
    
    # Usamos la fecha de hoy
    hoy = date.today()
    
    # Usamos tu función existente para calcular los totales
    consumed_cal, consumed_macros = get_total_intake_for_date(db, current_user, hoy)
    
    return {
        "fecha": str(hoy),
        "calorias_consumidas": consumed_cal,
        "macros_consumidos": consumed_macros
    }

@router.post("/intakes")
def create_intake(
    texto_ingesta: str = Body(..., example="Una doble cheese bacon del mcdonalds y un vaso de coca cola cero"),
    fecha: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registrar una ingesta del usuario pasándole texto libre. La IA estima todo.
    """
    try:
        # 1. Magia de la IA: analizamos el texto libre
        analisis = analyze_intake_with_groq(texto_ingesta)
        
        # 2. Formatear la fecha si viene
        f = date.fromisoformat(fecha) if fecha else None
        
        # 3. Guardar en la base de datos usando tu función existente
        intake = record_user_intake(
            db=db,
            user=current_user,
            alimentos=analisis["alimentos"],
            calorias=analisis["calorias"],
            macros=analisis["macros"],
            fecha=f
        )
        
        # 4. Devolvemos el ID y también lo que la IA ha calculado para mostrárselo al usuario
        return {
            "ok": True, 
            "intake_id": intake.id,
            "analisis_ia": analisis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al analizar la ingesta: {str(e)}")

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

   # 🔹 Guardar comidas en Base de Datos
    saved_meals: List[Meal] = []
    for comida in comidas_generadas:
        meal = Meal(
            plan_id=new_plan.id,
            dia=comida.get("dia", 1), # 🔹 Por defecto 1 (ideal para menú diario)
            turno=comida.get("turno", "comida"), # 🔹 Guardamos su turno real
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

    # 🔹 Construir menú completo agrupado por DÍA y luego por TURNO
    menu_full: Dict[str, Dict[str, List[dict]]] = {}
    menu_ids: Dict[str, Dict[str, List[int]]] = {}

    for meal in saved_meals:
        dia_str = str(meal.dia)
        turno = meal.turno

        # Inicializar el día si no existe
        if dia_str not in menu_full:
            menu_full[dia_str] = {"desayuno": [], "comida": [], "cena": []}
            menu_ids[dia_str] = {"desayuno": [], "comida": [], "cena": []}
        
        # Inicializar el turno si Groq se inventa uno nuevo (ej. "snack")
        if turno not in menu_full[dia_str]:
            menu_full[dia_str][turno] = []
            menu_ids[dia_str][turno] = []

        # Agregar la comida a su día y turno correspondiente
        menu_full[dia_str][turno].append(serialize_meal(meal))
        menu_ids[dia_str][turno].append(meal.id)

    # 🔹 Guardar mapping de IDs en el plan
    new_plan.menu = menu_ids
    db.commit()
    db.refresh(new_plan)

    print(f"[DEBUG] IDs agrupados: {menu_ids}")

    # 🔹 Adjuntar menú completo para la respuesta del Frontend
    new_plan.menu = menu_full
    return new_plan

@router.get("/menus", response_model=List[NutritionPlanRead])
def obtener_menus(
    tipo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Obtener los planes del usuario según si hay filtro de tipo o no
    query = db.query(NutritionPlan).filter(NutritionPlan.user_id == current_user.id)
    if tipo:
        query = query.filter(NutritionPlan.tipo == tipo)
    
    planes = query.order_by(NutritionPlan.created_at.desc()).all()

    # Si no hay planes, devolvemos lista vacía
    if not planes:
        return []

    resultado = []

    for plan in planes:
        # 2. Recuperar todas las comidas asociadas a este plan desde la DB
        meals = db.query(Meal).filter(Meal.plan_id == plan.id).all()

        # 3. Reconstruir la estructura del menú por día y turno
        menu_full: Dict[str, Dict[str, List[dict]]] = {}
        
        for meal in meals:
            dia_str = str(meal.dia)
            turno = meal.turno

            if dia_str not in menu_full:
                menu_full[dia_str] = {"desayuno": [], "almuerzo": [], "comida": [], "cena": []}
            
            if turno not in menu_full[dia_str]:
                menu_full[dia_str][turno] = []

            menu_full[dia_str][turno].append(serialize_meal(meal))

        # 4. Crear un diccionario con los datos del plan y el menú reconstruido
        plan_dict = {
            "id": plan.id,
            "user_id": plan.user_id,
            "tipo": plan.tipo,
            "calorias": plan.calorias,
            "macros": plan.macros,
            "created_at": plan.created_at,
            "menu": menu_full
        }
        
        resultado.append(plan_dict)

    return resultado

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
