from http.client import HTTPException
from sqlalchemy.orm import Session
from models.enums import Gender, Goal
from models.db_models import Meal, NutritionPlan, User, UserIntake
from typing import Optional, Dict
from datetime import date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import joinedload

def get_user_plan_by_type(db: Session, user: User, tipo: str):
    plan = db.query(NutritionPlan)\
        .options(joinedload(NutritionPlan.meals))\
        .filter(
            NutritionPlan.user_id == user.id,
            NutritionPlan.tipo == tipo
        )\
        .order_by(NutritionPlan.created_at.desc())\
        .first()

    if plan:
        plan.menu = build_full_menu(plan)
    print("MEALS COUNT:", len(plan.meals) if plan else 0)
    return plan

def build_full_menu(plan: NutritionPlan):
    if not plan.menu:
        # Si no hay mapping de IDs, devolver vacío
        return {"desayuno": [], "comida": [], "cena": []}

    menu_full = {}
    for turno, meal_ids in plan.menu.items():
        menu_full[turno] = [serialize_meal(meal) for meal in plan.meals if meal.id in meal_ids]
    return menu_full



def serialize_meal(meal: Meal) -> dict:
    """
    Convierte un objeto Meal en dict listo para la API.
    """
    return {
        "id": meal.id,
        "plan_id": meal.plan_id,
        "dia": meal.dia,       # 🔹 NUEVO
        "turno": meal.turno,   # 🔹 NUEVO
        "nombre": meal.nombre,
        "macros": meal.macros,
        "calorias": meal.calorias,
        "completed": meal.completed,
        "imagen_url": meal.imagen_url
    }


def calcular_macros(user: User):
    """
    Calcula calorías y macros aproximados según datos del usuario.
    """
    # BMR
    bmr = 10 * user.peso + 6.25 * user.altura - 5 * user.edad
    bmr += 5 if user.genero == Gender.male else -161

    activity_factors = {
        "sedentario": 1.2,
        "ligero": 1.375,
        "moderado": 1.55,
        "activo": 1.725,
        "muy_activo": 1.9
    }
    tdee = bmr * activity_factors.get(user.nivel_actividad, 1.2)

    if user.objetivo == Goal.lose:
        calories = tdee - 500
    elif user.objetivo == Goal.gain:
        calories = tdee + 500
    else:
        calories = tdee

    carbs_g = (calories * 0.5) / 4
    protein_g = (calories * 0.25) / 4
    fat_g = (calories * 0.25) / 9

    macros = {
        "carbohidratos_g": round(carbs_g),
        "proteinas_g": round(protein_g),
        "grasas_g": round(fat_g)
    }

    return round(calories), macros

def get_meal_by_plan_and_id(db: Session, plan_id: int, meal_id: int) -> Meal:
    meal = db.query(Meal).filter(
        Meal.id == meal_id,
        Meal.plan_id == plan_id
    ).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Comida no encontrada")
    return meal

def record_user_intake(db: Session, user: User, alimentos: List[Dict[str, Any]], calorias: int, macros: Dict[str, int], fecha: Optional[date] = None):
    from models.db_models import UserIntake
    fecha = fecha or date.today()
    intake = UserIntake(
        user_id=user.id,
        fecha=fecha,
        alimentos=alimentos,
        calorias=calorias,
        macros=macros
    )
    db.add(intake)
    db.commit()
    db.refresh(intake)
    return intake


def get_total_intake_for_date(db: Session, user: User, fecha: Optional[date] = None) -> Tuple[int, Dict[str, int]]:
    from models.db_models import UserIntake
    fecha = fecha or date.today()
    rows = db.query(UserIntake).filter(UserIntake.user_id == user.id, UserIntake.fecha == fecha).all()
    total_cal = sum(r.calorias or 0 for r in rows)
    total_macros = {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0}
    for r in rows:
        m = r.macros or {}
        total_macros["carbohidratos_g"] += m.get("carbohidratos_g", 0)
        total_macros["proteinas_g"] += m.get("proteinas_g", 0)
        total_macros["grasas_g"] += m.get("grasas_g", 0)
    return total_cal, total_macros


def calculate_gap_for_day(plan: NutritionPlan, consumed_cal: int, consumed_macros: Dict[str, int]) -> Dict[str, Any]:
    objetivo_cal = int(plan.calorias)
    objetivo_macros = plan.macros or {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0}

    calorias_restantes = max(0, objetivo_cal - consumed_cal)
    macros_restantes = {
        "carbohidratos_g": max(0, int(objetivo_macros.get("carbohidratos_g", 0) - consumed_macros.get("carbohidratos_g", 0))),
        "proteinas_g": max(0, int(objetivo_macros.get("proteinas_g", 0) - consumed_macros.get("proteinas_g", 0))),
        "grasas_g": max(0, int(objetivo_macros.get("grasas_g", 0) - consumed_macros.get("grasas_g", 0))),
    }
    return {"calorias_restantes": calorias_restantes, "macros_restantes": macros_restantes}

def generate_adjusted_menu(plan: NutritionPlan, gap: Dict[str, Any], user: User) -> Dict[str, List[Dict[str, Any]]]:
    """
    Genera un menú ajustado llamando a Groq para cuadrar el GAP del día.
    """
    from services.groq_client import generate_adjusted_menu_with_groq

    calorias_restantes = gap["calorias_restantes"]
    macros_restantes = gap["macros_restantes"]

    # 1. Si el usuario ya ha cumplido o se ha pasado de sus macros
    if calorias_restantes <= 50:
        return {
            "aviso": [{
                "nombre": "¡Has completado tus macros de hoy!",
                "alimentos": [],
                "macros": {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0},
                "calorias": 0,
                "completed": True
            }]
        }

    # 2. Si aún le faltan calorías, llamamos a la IA
    try:
        print(f"[IA] Recalculando menú para {calorias_restantes} kcal restantes...")
        nuevo_menu = generate_adjusted_menu_with_groq(
            macros_restantes,
            calorias_restantes,
            user.preferencias or [],
            user.restricciones or []
        )
        return nuevo_menu

    except Exception as e:
        print(f"[ERROR RECALCULO IA] {e}")
        # Fallback de emergencia si la IA falla
        return {"error": [{"nombre": "Error al recalcular", "calorias": calorias_restantes}]}


def save_plan_adjustment(db: Session, plan: NutritionPlan, adjusted_menu: Dict[str, Any], fecha: Optional[date] = None):
    """
    Guarda en DB un ajuste del plan para esa fecha.
    """
    from models.db_models import PlanAdjustment
    fecha = fecha or date.today()
    adjustment = PlanAdjustment(
        plan_id=plan.id,
        fecha=fecha,
        adjusted_menu=adjusted_menu
    )
    db.add(adjustment)
    db.commit()
    db.refresh(adjustment)
    return adjustment