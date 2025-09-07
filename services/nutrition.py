from requests import Session
from models.enums import Gender, Goal
from models.db_models import NutritionPlan, User
from typing import Optional

def get_user_plan_by_type(db: Session, user: User, tipo: str) -> Optional[NutritionPlan]:
    return db.query(NutritionPlan).filter(
        NutritionPlan.user_id == user.id,
        NutritionPlan.tipo == tipo
    ).order_by(NutritionPlan.created_at.desc()).first()

def calcular_macros(data):
    # Calcular BMR
    bmr = 10 * data.peso + 6.25 * data.altura - 5 * data.edad
    bmr += 5 if data.genero == Gender.male else -161

    activity_factors = {
        "sedentario": 1.2,
        "ligero": 1.375,
        "moderado": 1.55,
        "activo": 1.725,
        "muy_activo": 1.9
    }
    tdee = bmr * activity_factors.get(data.nivel_actividad, 1.2)

    if data.objetivo == Goal.lose:
        calories = tdee - 500
    elif data.objetivo == Goal.gain:
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
