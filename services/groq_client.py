# services/groq_client.py
import re
import requests, json
from core.config import settings

def generate_menu_with_groq(calories, macros, preferencias, restricciones, prompt_template):
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
    json_start = content.find('{')
    json_end = content.rfind('}') + 1
    json_str = content[json_start:json_end]

    return json.loads(json_str)

# services/groq_client.py
import requests, json
from core.config import settings

def generate_meal_with_groq(meal_info, preferencias, restricciones):
    """
    Genera una comida alternativa con macros similares usando la IA de Groq.
    Devuelve un dict seguro.
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
        return json.loads(content)
    except json.JSONDecodeError:
        # 🔹 Como fallback, buscamos la primera llave que tenga sentido
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == -1:
            raise ValueError("No se encontró JSON válido en la respuesta de la IA")
        try:
            return json.loads(content[start:end])
        except json.JSONDecodeError as e:
            # Si aún falla, devolvemos algo genérico para no romper el endpoint
            return {
                "nombre": meal_info.get("nombre", "Comida alternativa"),
                "ingredientes": [],
                "macros": meal_info.get("macros", {"carbohidratos_g":0,"proteinas_g":0,"grasas_g":0}),
                "calorias": meal_info.get("calorias", 0)
            }
