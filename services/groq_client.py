import re
import json
from typing import Dict, Any, List

# 🔥 NUEVA LIBRERÍA OFICIAL DE GOOGLE
from google import genai
from google.genai import types

from core.config import settings
from core.prompts import ANALISIS_INGESTA_PROMPT, RETO_GAMIFICACION_PROMPT

# ==========================================
# 🛠️ CONFIGURACIÓN GEMINI Y HELPERS
# ==========================================

# Inicializar el nuevo cliente de Gemini
client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Configuración estricta para forzar JSON en la nueva API
json_config = types.GenerateContentConfig(
    response_mime_type="application/json"
)

def _extract_json(content: str, fallback_data: Any = None) -> Any:
    """Extrae JSON ultra-robusto."""
    if fallback_data is None:
        fallback_data = [{
            "dia": 1,
            "turno": "desayuno",
            "nombre": "Menú de Rescate (Servidores Ocupados)",
            "ingredientes": [{"nombre": "Alimentos variados", "cantidad_g": 100}],
            "macros": {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0},
            "calorias": 0,
            "image_search_term": "healthy meal"
        }]

    try:
        content_clean = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        
        try:
            return json.loads(content_clean)
        except json.JSONDecodeError:
            pass
            
        match_md = re.search(r'```(?:json)?(.*?)```', content_clean, re.DOTALL)
        if match_md:
            return json.loads(match_md.group(1).strip())
            
        match_raw = re.search(r'(\[.*\]|\{.*\})', content_clean, re.DOTALL)
        if match_raw:
            return json.loads(match_raw.group(1).strip())
            
        return fallback_data
        
    except Exception as e:
        print(f"[ERROR GEMINI EXTRACTION] Fallo crítico al parsear JSON: {e}")
        return fallback_data

# ==========================================
# 🤖 SERVICIOS DE IA PÚBLICOS (Conectados a Gemini)
# ==========================================

def analyze_image_with_groq(file_bytes: bytes, mime_type: str) -> dict:
    prompt_texto = (
        "Eres un nutricionista experto. Analiza la siguiente imagen de un plato de comida. "
        "Identifica ingredientes, estima ración (g) y calcula valores nutricionales. "
        "Responde SOLO con JSON. Formato: {'nombre_plato': 'str', 'calorias': int, 'macros': {'proteinas': int, 'carbohidratos': int, 'grasas': int}, 'ingredientes': ['str']}"
    )

    try:
        # Formato de imagen para la nueva SDK
        image_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[image_part, prompt_texto],
            config=json_config
        )
        return _extract_json(response.text)
    except Exception as e:
        print(f"[ERROR VISION GEMINI] {e}")
        return {"nombre_plato": "Plato no reconocido", "calorias": 0, "macros": {"proteinas": 0, "carbohidratos": 0, "grasas": 0}, "ingredientes": []}


def generate_challenges_with_groq(gap_calorias: int, gap_macros: dict) -> list:
    prompt = f"{RETO_GAMIFICACION_PROMPT}\n\nFaltan por consumir:\nCalorías: {gap_calorias} kcal\nMacros: {gap_macros}"
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=json_config
        )
        return _extract_json(response.text).get("retos", [])
    except Exception as e:
        print(f"[ERROR GEMINI CHALLENGES] {e}")
        return []


def analyze_intake_with_groq(texto_ingesta: str) -> dict:
    prompt = f"{ANALISIS_INGESTA_PROMPT}\n\nIngesta del usuario: '{texto_ingesta}'"
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=json_config
        )
        return _extract_json(response.text)
    except Exception as e:
        print(f"[ERROR GEMINI INTAKE] {e}")
        return {"calorias": 0, "macros": {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0}, "alimentos": []}


def generate_menu_with_groq(calories, macros, preferencias, restricciones, prompt_template):
    pref_txt = ', '.join(preferencias) if preferencias else 'ninguna'
    restr_txt = ', '.join(restricciones) if restricciones else 'ninguna'

    prompt = prompt_template.format(
        calories=round(calories), carbs=round(macros.get('carbohidratos_g', 0)),
        proteins=round(macros.get('proteinas_g', 0)), fats=round(macros.get('grasas_g', 0)),
        preferencias=pref_txt, restricciones=restr_txt
    )
    
    try:
        print(f"[DEBUG GEMINI] Generando menú con {settings.GEMINI_MODEL}...")
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=json_config
        )
        menu_data = _extract_json(response.text)
        
    except Exception as e:
        print(f"[PROD ALERT] Fallo crítico de conexión con Gemini: {e}")
        menu_data = _extract_json("")

    if isinstance(menu_data, list):
        menu_list = menu_data
    elif isinstance(menu_data, dict):
        menu_list = menu_data.get("comidas", [])
    else:
        menu_list = []
    
    if not isinstance(menu_list, list) or len(menu_list) == 0:
        print("[PROD ALERT] El fallback falló, inyectando menú de emergencia duro.")
        menu_list = [{
            "dia": 1, "turno": "desayuno", "nombre": "Menú de Emergencia",
            "ingredientes": [{"nombre": "Alimentos básicos", "cantidad_g": 100}],
            "macros": {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0},
            "calorias": 0, "completed": False
        }]

    for comida in menu_list:
        comida["completed"] = False
        
    return menu_list


def generate_meal_with_groq(meal_info, preferencias, restricciones):
    pref_txt = ', '.join(preferencias) if preferencias else 'ninguna'
    restr_txt = ', '.join(restricciones) if restricciones else 'ninguna'

    prompt = f"""
    Eres un nutricionista experto. Genera una comida alternativa con macros cercanos a la original.
    Preferencias: {pref_txt}. Restricciones: {restr_txt}.
    Devuelve SOLO JSON con formato: {{"nombre": "str", "ingredientes": [{{"nombre": "str", "cantidad_g": int}}], "macros": {{"carbohidratos_g": int, "proteinas_g": int, "grasas_g": int}}, "calorias": int}}
    Comida original: {json.dumps(meal_info, ensure_ascii=False)}
    """

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=json_config
        )
        meal_dict = _extract_json(response.text)
    except Exception as e:
        print(f"[WARN] JSON inválido para comida alternativa: {e}")
        meal_dict = {}

    for key in ["nombre", "ingredientes", "macros", "calorias"]:
        if key not in meal_dict:
            meal_dict[key] = meal_info.get(key, [] if key == "ingredientes" else 0)

    meal_dict["completed"] = False
    return meal_dict


def generate_adjusted_menu_with_groq(macros_restantes, calorias_restantes, preferencias, restricciones):
    pref_txt = ', '.join(preferencias) if preferencias else 'ninguna'
    restr_txt = ', '.join(restricciones) if restricciones else 'ninguna'

    prompt = f"""
    El usuario ya ha consumido parte de su dieta de hoy. Le quedan:
    Calorías: {calorias_restantes} kcal | Carbohidratos: {macros_restantes.get('carbohidratos_g', 0)} g | Proteínas: {macros_restantes.get('proteinas_g', 0)} g | Grasas: {macros_restantes.get('grasas_g', 0)} g
    Preferencias: {pref_txt}. Restricciones: {restr_txt}.
    Devuelve SOLO JSON: {{"comida": [{{...}}], "cena": [{{...}}]}} (omite turnos que no procedan).
    """

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=json_config
        )
        menu_dict = _extract_json(response.text)
        
        for turno, comidas in menu_dict.items():
            for comida in comidas:
                comida["completed"] = False
                
        return menu_dict
    except Exception as e:
        print(f"[ERROR GEMINI ADJUST] {e}")
        return {}