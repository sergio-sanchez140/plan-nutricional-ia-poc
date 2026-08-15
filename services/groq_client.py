# services/groq_client.py
# services/groq_client.py
import re
import requests
import json
from core.config import settings
from core.prompts import ANALISIS_INGESTA_PROMPT
from core.prompts import RETO_GAMIFICACION_PROMPT
import base64

def analyze_image_with_groq(file_bytes: bytes, mime_type: str) -> dict:
    """Procesa los bytes de una imagen en Base64 y consulta al modelo de visión de Groq."""
    
    # 1. Convertir la imagen a Base64
    base64_image = base64.b64encode(file_bytes).decode('utf-8')
    data_url = f"data:{mime_type};base64,{base64_image}"

    # 2. Construir la petición HTTP con el modelo de visión
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt_texto = (
        "Eres un nutricionista experto. Analiza la siguiente imagen de un plato de comida. "
        "Identifica los ingredientes principales, estima la ración media (en gramos) y calcula los valores nutricionales aproximados. "
        "Debes responder ÚNICA Y EXCLUSIVAMENTE con un JSON válido, sin Markdown extra ni texto antes o después. "
        "Estructura exacta:\n"
        '{"nombre_plato": "string", "calorias": 0, "macros": {"proteinas": 0, "carbohidratos": 0, "grasas": 0}, "ingredientes": ["string"]}'
    )

    payload = {
        "model": "llama-3.2-11b-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_texto},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]
            }
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"[ERROR GROQ VISION] {response.status_code} - {response.text}")
        response.raise_for_status()

    contenido = response.json()["choices"][0]["message"]["content"]
    return json.loads(contenido)

def generate_challenges_with_groq(gap_calorias: int, gap_macros: dict) -> list:
    prompt = f"{RETO_GAMIFICACION_PROMPT}\n\nFaltan por consumir:\nCalorías: {gap_calorias} kcal\nMacros: {gap_macros}"
    
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Eres un motor de gamificación que responde en JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7, 
        "response_format": {"type": "json_object"}
    }
    
    response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    
    contenido = response.json()["choices"][0]["message"]["content"]
    return json.loads(contenido).get("retos", [])

def analyze_intake_with_groq(texto_ingesta: str) -> dict:
    """Envía el texto libre del usuario a la IA para estimar calorías y macros."""
    prompt = f"{ANALISIS_INGESTA_PROMPT}\n\nIngesta del usuario: '{texto_ingesta}'"
    
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Eres un experto en nutrición que devuelve SOLO JSON válido."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2, 
        "response_format": {"type": "json_object"}
    }
    
    response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"[ERROR GROQ] {response.status_code} - {response.text}")
    response.raise_for_status()
    
    contenido = response.json()["choices"][0]["message"]["content"]
    return json.loads(contenido)

def generate_menu_with_groq(calories, macros, preferencias, restricciones, prompt_template):
    """
    Genera un menú completo con IA y devuelve una lista de objetos Meal.
    """
    preferencias_text = ', '.join(preferencias) if preferencias else 'ninguna'
    restricciones_text = ', '.join(restricciones) if restricciones else 'ninguna'

    # 🔹 Ya no concatenamos texto aquí, el esquema viene en el prompt_template
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
            {"role": "system", "content": "Eres un nutricionista que devuelve listas JSON perfectas."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        # 🔹 Subimos los tokens para permitir menús semanales largos
        "max_tokens": 4000 
    }

    response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"[ERROR GROQ] {response.status_code} - {response.text}")
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    print(f"[DEBUG] Respuesta cruda: {content[:200]}...")

    # 🔹 Buscar la lista plana [...]
    match = re.search(r'\[.*\]', content, re.DOTALL)
    if not match:
        raise ValueError("No se encontró una lista JSON válida en la IA")
    
    menu_list = json.loads(match.group())
    
    # 🔹 Asegurar que no estén completadas por defecto
    for comida in menu_list:
        comida["completed"] = False
        
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

def generate_adjusted_menu_with_groq(macros_restantes, calorias_restantes, preferencias, restricciones):
    """
    Solicita a la IA un menú para compensar exactamente los macros y calorías restantes.
    """
    preferencias_text = ', '.join(preferencias) if preferencias else 'ninguna'
    restricciones_text = ', '.join(restricciones) if restricciones else 'ninguna'

    prompt = f"""
    Eres un nutricionista experto. El usuario ya ha consumido parte de su dieta de hoy.
    Le quedan EXACTAMENTE estas metas para completar el día:
    - Calorías restantes: {calorias_restantes} kcal
    - Carbohidratos restantes: {macros_restantes.get('carbohidratos_g', 0)} g
    - Proteínas restantes: {macros_restantes.get('proteinas_g', 0)} g
    - Grasas restantes: {macros_restantes.get('grasas_g', 0)} g

    Preferencias: {preferencias_text}. Restricciones: {restricciones_text}.

    Genera las comidas necesarias para cubrir lo mejor posible estos macros restantes.
    Distribúyelas lógicamente. Si faltan muchas calorías, divídelo en "comida" y "cena". Si faltan pocas, solo "cena" o "snack".

    Devuelve SOLO un JSON válido con esta estructura (omite turnos que no procedan):
    {{
      "comida": [
        {{
          "nombre": "string",
          "ingredientes": [{{"nombre": "string", "cantidad_g": 100}}],
          "macros": {{"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0}},
          "calorias": 0
        }}
      ],
      "cena": [ ... ]
    }}
    """

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Eres un nutricionista experto que responde SOLO con JSON válido."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"[ERROR GROQ] {response.status_code} - {response.text}")
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    
    # Extraer JSON de forma segura
    import re
    import json
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if not match:
        raise ValueError("No se encontró JSON válido en el recálculo")
    
    menu_dict = json.loads(match.group())
    
    # Asegurar que todas las comidas tienen el flag "completed" a False
    for turno, comidas in menu_dict.items():
        for comida in comidas:
            comida["completed"] = False
            
    return menu_dict
