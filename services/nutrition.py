from sqlalchemy.orm import Session
from models.enums import Gender, Goal
from models.db_models import Meal, NutritionPlan, User
from typing import Optional, Dict


def get_user_plan_by_type(db: Session, user: User, tipo: str) -> Optional[NutritionPlan]:
    plan = db.query(NutritionPlan).filter(
        NutritionPlan.user_id == user.id,
        NutritionPlan.tipo == tipo
    ).order_by(NutritionPlan.created_at.desc()).first()

    if plan:
        plan.menu = build_full_menu(plan)
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
    Convierte un objeto Meal en dict listo para la API, incluyendo plan_id.
    """
    return {
        "id": meal.id,
        "plan_id": meal.plan_id,  # 🔹 añadido
        "nombre": meal.nombre,
        "macros": meal.macros,
        "calorias": meal.calorias,
        "completed": meal.completed
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
