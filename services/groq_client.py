# services/groq_client.py
import re
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

    # 🔹 Prompt reforzado con ejemplo
    prompt = prompt_template.format(
        calories=round(calories),
        carbs=round(macros.get('carbohidratos_g', 0)),
        proteins=round(macros.get('proteinas_g', 0)),
        fats=round(macros.get('grasas_g', 0)),
        preferencias=preferencias_text,
        restricciones=restricciones_text
    ) + """
Devuelve SOLO un JSON válido con la siguiente estructura para cada comida:

{
  "desayuno": [
    {
      "nombre": "string",
      "ingredientes": [{"nombre": "string", "cantidad_g": int}],
      "macros": {"carbohidratos_g": int, "proteinas_g": int, "grasas_g": int},
      "calorias": int
    }
  ],
  "comida": [...],
  "cena": [...]
}

No agregues texto fuera del JSON. Cada comida debe tener todos los campos.
"""

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
        "max_tokens": 1500
    }

    response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload)
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    print(f"[DEBUG] Contenido crudo recibido de la IA: {content}")

    # 🔹 Intentamos cargar JSON directamente
    try:
        menu_dict = json.loads(content)
    except json.JSONDecodeError:
        # Buscar primer bloque JSON válido
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == -1:
            raise ValueError("No se encontró JSON válido en la respuesta de la IA")
        menu_dict = json.loads(content[start:end])

    # 🔹 Convertimos dict por turnos a lista de comidas individuales
    menu_list = []
    for turno, comidas in menu_dict.items():  # desayuno/comida/cena
        if not isinstance(comidas, list):
            raise ValueError(f"Esperaba lista de comidas en turno '{turno}', pero se recibió {type(comidas)}")
        for comida in comidas:
            # Validar estructura mínima
            comida_validada = {
                "nombre": comida.get("nombre", "Comida"),
                "ingredientes": comida.get("ingredientes", []),
                "macros": comida.get("macros", {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0}),
                "calorias": comida.get("calorias", 0),
                "completed": False
            }
            menu_list.append({"turno": turno, **comida_validada})
            print(f"[DEBUG] Comida final agregada: {comida_validada}")

    print(f"[DEBUG] Menu final generado: {menu_list}")
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
    print(f"[DEBUG] Contenido crudo de la IA para comida alternativa: {content}")

    # 🔹 Intentar cargar JSON directamente
    try:
        meal_dict = json.loads(content)
    except json.JSONDecodeError:
        # 🔹 Extraer primer bloque JSON válido usando regex
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if not match:
            print("[WARN] No se encontró JSON válido, se devuelve fallback.")
            return {
                "nombre": meal_info.get("nombre", "Comida alternativa"),
                "ingredientes": meal_info.get("ingredientes", []),
                "macros": meal_info.get("macros", {"carbohidratos_g":0,"proteinas_g":0,"grasas_g":0}),
                "calorias": meal_info.get("calorias", 0),
                "completed": False
            }
        try:
            meal_dict = json.loads(match.group())
        except json.JSONDecodeError:
            print("[WARN] JSON inválido tras regex, se devuelve fallback.")
            return {
                "nombre": meal_info.get("nombre", "Comida alternativa"),
                "ingredientes": meal_info.get("ingredientes", []),
                "macros": meal_info.get("macros", {"carbohidratos_g":0,"proteinas_g":0,"grasas_g":0}),
                "calorias": meal_info.get("calorias", 0),
                "completed": False
            }

    # 🔹 Validación mínima
    for key in ["nombre", "ingredientes", "macros", "calorias"]:
        if key not in meal_dict:
            meal_dict[key] = meal_info.get(key, [] if key == "ingredientes" else 0)

    meal_dict["completed"] = False
    print(f"[DEBUG] Comida alternativa final: {meal_dict}")
    return meal_dict
