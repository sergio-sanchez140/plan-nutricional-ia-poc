from fastapi import APIRouter
from models.user_data import UserData
from services.nutrition import calcular_macros
from services.groq_client import generate_menu_with_groq

router = APIRouter()

@router.post("/plan-nutricional-ia")
async def generate_plan_ai(data: UserData):
    calories, macros = calcular_macros(data)
    menu_diario = generate_menu_with_groq(calories, macros, data.preferencias, data.restricciones)

    return {
        "calorias": calories,
        "macros": macros,
        "menu_diario": menu_diario
    }
