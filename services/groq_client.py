import re
import requests
import json
import base64
from typing import Dict, Any, List

from core.config import settings
from core.prompts import ANALISIS_INGESTA_PROMPT, RETO_GAMIFICACION_PROMPT

# ==========================================
# 🛠️ FUNCIONES PRIVADAS (HELPERS)
# ==========================================

def _call_groq_api(messages: List[Dict], model: str, temperature: float = 0.7, max_tokens: int = 1000, json_mode: bool = True) -> str:
    """Centraliza las peticiones HTTP a la API de Groq para no repetir código."""
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"[ERROR GROQ] {response.status_code} - {response.text}")
        response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]

def _extract_json(content: str) -> Any:
    """Extrae JSON robusto ignorando texto o markdown extra."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Busca el primer bloque que parezca un diccionario {} o array []
        match = re.search(r'(\{.*\}|\[.*\])', content, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("No se encontró JSON válido en la respuesta de Groq")

# ==========================================
# 🤖 SERVICIOS DE IA PÚBLICOS
# ==========================================

def analyze_image_with_groq(file_bytes: bytes, mime_type: str) -> dict:
    base64_image = base64.b64encode(file_bytes).decode('utf-8')
    data_url = f"data:{mime_type};base64,{base64_image}"

    prompt_texto = (
        "Eres un nutricionista experto. Analiza la siguiente imagen de un plato de comida. "
        "Identifica ingredientes, estima ración (g) y calcula valores nutricionales. "
        "Responde SOLO con JSON. Formato: {'nombre_plato': 'str', 'calorias': int, 'macros': {'proteinas': int, 'carbohidratos': int, 'grasas': int}, 'ingredientes': ['str']}"
    )

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt_texto},
            {"type": "image_url", "image_url": {"url": data_url}}
        ]
    }]

    content = _call_groq_api(messages, settings.GROQ_VISION_MODEL, temperature=0.2)
    return _extract_json(content)

def generate_challenges_with_groq(gap_calorias: int, gap_macros: dict) -> list:
    prompt = f"{RETO_GAMIFICACION_PROMPT}\n\nFaltan por consumir:\nCalorías: {gap_calorias} kcal\nMacros: {gap_macros}"
    messages = [
        {"role": "system", "content": "Eres un motor de gamificación que responde en JSON."},
        {"role": "user", "content": prompt}
    ]
    content = _call_groq_api(messages, settings.GROQ_MODEL)
    return _extract_json(content).get("retos", [])

def analyze_intake_with_groq(texto_ingesta: str) -> dict:
    prompt = f"{ANALISIS_INGESTA_PROMPT}\n\nIngesta del usuario: '{texto_ingesta}'"
    messages = [
        {"role": "system", "content": "Eres un experto en nutrición que devuelve SOLO JSON válido."},
        {"role": "user", "content": prompt}
    ]
    content = _call_groq_api(messages, settings.GROQ_MODEL, temperature=0.2)
    return _extract_json(content)

def generate_menu_with_groq(calories, macros, preferencias, restricciones, prompt_template):
    pref_txt = ', '.join(preferencias) if preferencias else 'ninguna'
    restr_txt = ', '.join(restricciones) if restricciones else 'ninguna'

    prompt = prompt_template.format(
        calories=round(calories), carbs=round(macros.get('carbohidratos_g', 0)),
        proteins=round(macros.get('proteinas_g', 0)), fats=round(macros.get('grasas_g', 0)),
        preferencias=pref_txt, restricciones=restr_txt
    )

    messages = [
        {"role": "system", "content": "Eres un nutricionista que devuelve listas JSON perfectas."},
        {"role": "user", "content": prompt}
    ]
    
    # ⚠️ Desactivamos json_mode aquí porque Groq exige que la raíz sea un objeto ({}), no una lista plana ([])
    content = _call_groq_api(messages, settings.GROQ_MODEL, max_tokens=4000, json_mode=False)
    
    menu_list = _extract_json(content)
    if not isinstance(menu_list, list):
        raise ValueError("Se esperaba una lista de menús")

    for comida in menu_list:
        comida["completed"] = False
    return menu_list

def generate_meal_with_groq(meal_info, preferencias, restricciones):
    pref_txt = ', '.join(preferencias) if preferencias else 'ninguna'
    restr_txt = ', '.join(restricciones) if restricciones else 'ninguna'

    prompt = f"""
    Eres un nutricionista experto. Genera una comida alternativa con macros cercanos a la original.
    Preferencias: {pref_txt}. Restricciones: {restr_txt}.
    Devuelve SOLO JSON con formato: {{"nombre": "str", "ingredientes": [{{"nombre": "str", "cantidad_g": int}}], "macros": {{"carbohidratos_g": int, "proteinas_g": int, "grasas_g": int}}, "calorias": int, "image_search_term": "str (2-3 keywords en inglés, ej: 'grilled salmon')"}}
    Comida original: {json.dumps(meal_info, ensure_ascii=False)}
    """

    messages = [
        {"role": "system", "content": "Eres un nutricionista experto que genera comidas en JSON."},
        {"role": "user", "content": prompt}
    ]
    content = _call_groq_api(messages, settings.GROQ_MODEL, max_tokens=600)

    try:
        meal_dict = _extract_json(content)
    except Exception:
        print("[WARN] JSON inválido para comida alternativa, se usa fallback.")
        meal_dict = {}

    # Validación mínima de seguridad (Fallback)
    for key in ["nombre", "ingredientes", "macros", "calorias"]:
        if key not in meal_dict:
            meal_dict[key] = meal_info.get(key, [] if key == "ingredientes" else 0)
            
    # Validación extra para la imagen
    if "image_search_term" not in meal_dict:
        meal_dict["image_search_term"] = "healthy meal"

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

    messages = [
        {"role": "system", "content": "Eres un nutricionista experto que responde SOLO con JSON válido."},
        {"role": "user", "content": prompt}
    ]
    content = _call_groq_api(messages, settings.GROQ_MODEL, max_tokens=1000)
    
    menu_dict = _extract_json(content)
    for turno, comidas in menu_dict.items():
        for comida in comidas:
            comida["completed"] = False
            
    return menu_dict