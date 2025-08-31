# routes/nutrition_routes.py
from fastapi import APIRouter
from models.user_data import UserUpdate
from services.nutrition import calcular_macros
from services.groq_client import generate_menu_with_groq
from core.prompts import (
    MENU_DIARIO_PROMPT,
    MENU_SEMANAL_PROMPT,
    MENU_MENSUAL_PROMPT,
    SNACK_DIARIO_PROMPT,
    SUSTITUCIONES_PROMPT
)

router = APIRouter()

# 🔹 Menú diario
@router.post("/plan-nutricional-daily")
async def generate_plan_daily(data: UserUpdate):
    calories, macros = calcular_macros(data)
    menu_diario = generate_menu_with_groq(
        calories, macros, data.preferencias or [], data.restricciones or [], MENU_DIARIO_PROMPT
    )
    return {
        "calorias": calories,
        "macros": macros,
        "menu_diario": menu_diario
    }

# 🔹 Menú semanal
@router.post("/plan-nutricional-weekly")
async def generate_weekly_plan(data: UserUpdate):
    calories, macros = calcular_macros(data)
    menu_semanal = generate_menu_with_groq(
        calories, macros, data.preferencias or [], data.restricciones or [], MENU_SEMANAL_PROMPT
    )
    return {
        "calorias": calories,
        "macros": macros,
        "menu_semanal": menu_semanal
    }

# 🔹 Menú mensual
@router.post("/plan-nutricional-monthly")
async def generate_monthly_plan(data: UserUpdate):
    calories, macros = calcular_macros(data)
    menu_mensual = generate_menu_with_groq(
        calories, macros, data.preferencias or [], data.restricciones or [], MENU_MENSUAL_PROMPT
    )
    return {
        "calorias": calories,
        "macros": macros,
        "menu_mensual": menu_mensual
    }

# 🔹 Snacks diarios
@router.post("/snacks-dailys")
async def generate_snacks(data: UserUpdate):
    calories, macros = calcular_macros(data)
    snacks = generate_menu_with_groq(
        calories, macros, data.preferencias or [], data.restricciones or [], SNACK_DIARIO_PROMPT
    )
    return {
        "calorias": calories,
        "macros": macros,
        "snacks": snacks
    }

# 🔹 Sustituciones de alimentos
@router.get("/substitutions")
async def generate_substitutions(alimento: str):
    # Para sustituciones no necesitamos macros/calorías
    menu_sustituciones = generate_menu_with_groq(
        calories=0, macros={}, preferencias=[], restricciones=[],
        prompt_template=SUSTITUCIONES_PROMPT.format(alimento=alimento)
    )
    return {
        "alimento": alimento,
        "sustituciones": menu_sustituciones
    }
