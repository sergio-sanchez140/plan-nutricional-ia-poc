# services/groq_client.py
import requests
import json
from core.config import settings

def generate_menu_with_groq(calories, macros, preferencias, restricciones, prompt_template):
    """
    Genera un menú completo con IA y lo devuelve como lista de comidas individuales.
    Cada comida tendrá:
      - turno: desayuno, comida, cena
      - nombre
      - macros
      - calorías
    """
    preferencias_text = ', '.join(preferencias) if preferencias else 'ninguna'
    restricciones_text = ', '.join(restricciones) if restricciones else 'ninguna'

    prompt = prompt_template.format(
        calories=round(calories),
        carbs=round(macros.get('carbohidratos_g', 0)),
        proteins=round(macros.get('proteinas_g', 0)),
        fats=round(macros.get('grasas_g', 0)),
        preferencias=preferencias_text,
        restricciones=restricciones_text
    )

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Eres un nutricionista experto que genera menús en formato JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload)
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]

    # 🔹 Intentamos cargar JSON directamente
    try:
        menu_dict = json.loads(content)
    except json.JSONDecodeError:
        # 🔹 Fallback: buscamos la primera llave que tenga sentido
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == -1:
            raise ValueError("No se encontró JSON válido en la respuesta de la IA")
        menu_dict = json.loads(content[start:end])

    # 🔹 Convertimos dict por turnos a lista de comidas individuales
    menu_list = []
    for turno, comidas in menu_dict.items():  # desayuno/comida/cena
        for comida in comidas:
            menu_list.append({
                "turno": turno,
                "nombre": comida.get("nombre", "Comida"),
                "ingredientes": comida.get("ingredientes", []),
                "macros": comida.get("macros", {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0}),
                "calorias": comida.get("calorias", 0),
                "completed": False  # por defecto
            })

    return menu_list


def generate_meal_with_groq(meal_info, preferencias, restricciones):
    """
    Genera una comida alternativa con macros similares usando la IA de Groq.
    Devuelve un dict listo para insertar en la tabla Meal.
    """
    preferencias_text = ', '.join(preferencias) if preferencias else 'ninguna'
    restricciones_text = ', '.join(restricciones) if restricciones else 'ninguna'

    prompt = f"""
Eres un nutricionista experto. Genera una comida alternativa
con los macros lo más cercanos posibles a la comida original.
Respeta preferencias: {preferencias_text}.
Evita restricciones: {restricciones_text}.
Devuelve SOLO un JSON válido con la estructura:

{{
    "nombre": "string",
    "ingredientes": [{{"nombre": "string", "cantidad_g": int}}],
    "macros": {{"carbohidratos_g": int, "proteinas_g": int, "grasas_g": int}},
    "calorias": int
}}

Comida original:
{json.dumps(meal_info, ensure_ascii=False)}
"""

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Eres un nutricionista experto que genera comidas en JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 600
    }

    response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]

    # 🔹 Intentamos cargar JSON directamente
    try:
        meal_dict = json.loads(content)
    except json.JSONDecodeError:
        # 🔹 Como fallback, buscamos la primera llave que tenga sentido
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == -1:
            # Devolvemos dict seguro para no romper el endpoint
            return {
                "nombre": meal_info.get("nombre", "Comida alternativa"),
                "ingredientes": [],
                "macros": meal_info.get("macros", {"carbohidratos_g":0,"proteinas_g":0,"grasas_g":0}),
                "calorias": meal_info.get("calorias", 0),
                "completed": False
            }
        try:
            meal_dict = json.loads(content[start:end])
        except json.JSONDecodeError:
            return {
                "nombre": meal_info.get("nombre", "Comida alternativa"),
                "ingredientes": [],
                "macros": meal_info.get("macros", {"carbohidratos_g":0,"proteinas_g":0,"grasas_g":0}),
                "calorias": meal_info.get("calorias", 0),
                "completed": False
            }

    # 🔹 Añadimos completed por defecto
    meal_dict["completed"] = False
    return meal_dict
