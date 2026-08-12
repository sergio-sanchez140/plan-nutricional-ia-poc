# app/core/prompts.py

# app/core/prompts.py

# 🔹 Formato estricto para la IA (Lista plana con llaves dobles para escapar el .format)
JSON_SCHEMA_INFO = """
Devuelve SOLO un JSON válido. El JSON debe ser UNA LISTA PLANA de objetos.
Estructura exacta que debes seguir:
[
  {{
    "dia": 1, 
    "turno": "desayuno", 
    "nombre": "Avena con frutas",
    "ingredientes": [{{"nombre": "Avena", "cantidad_g": 50}}],
    "macros": {{"carbohidratos_g": 30, "proteinas_g": 10, "grasas_g": 5}},
    "calorias": 200
  }}
]
No agregues texto fuera del JSON.
"""

# 🔹 Menú diario
MENU_DIARIO_PROMPT = """
Eres un nutricionista experto. Genera un menú para 1 DÍA.
Requisitos:
- Calorías diarias: {calories} kcal
- Macronutrientes: {carbs}g carbohidratos, {proteins}g proteínas, {fats}g grasas
- Preferencias: {preferencias}
- Restricciones: {restricciones}
""" + JSON_SCHEMA_INFO

# 🔹 Menú semanal
MENU_SEMANAL_PROMPT = """
Eres un nutricionista experto. Genera un plan de comidas para 7 DÍAS.
Requisitos por día:
- Calorías diarias: {calories} kcal
- Macronutrientes: {carbs}g carbohidratos, {proteins}g proteínas, {fats}g grasas
- Preferencias: {preferencias}
- Restricciones: {restricciones}

IMPORTANTE: Debes generar las comidas desde el "dia": 1 hasta el "dia": 7.
""" + JSON_SCHEMA_INFO

# 🔹 Menú mensual (Nota: Puede consumir muchos tokens de IA)
MENU_MENSUAL_PROMPT = """
Eres un nutricionista experto. Genera un plan de comidas para 30 DÍAS.
Requisitos por día:
- Calorías diarias: {calories} kcal
- Macronutrientes: {carbs}g carbohidratos, {proteins}g proteínas, {fats}g grasas
- Preferencias: {preferencias}
- Restricciones: {restricciones}
""" + JSON_SCHEMA_INFO