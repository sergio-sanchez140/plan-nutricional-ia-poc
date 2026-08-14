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

# 🔹 Prompt para analizar una ingesta en lenguaje natural
ANALISIS_INGESTA_PROMPT = """
Eres un experto en nutrición. El usuario te dirá lo que ha comido en lenguaje natural.
Tu objetivo es estimar las calorías y macronutrientes totales de esa ingesta.
Haz tu mejor estimación basándote en alimentos estándar o marcas conocidas si se mencionan (ej: McDonald's).

Devuelve SOLO un JSON válido con esta estructura exacta (usar llaves dobles para el esquema):
{{
  "calorias": 1200,
  "macros": {{
    "carbohidratos_g": 100,
    "proteinas_g": 50,
    "grasas_g": 45
  }},
  "alimentos": [
    {{"nombre": "Doble Cheese Bacon McDonald's", "cantidad_g": 250}},
    {{"nombre": "Patatas fritas medianas", "cantidad_g": 110}}
  ]
}}
No incluyas NINGÚN texto fuera del JSON.
"""

RETO_GAMIFICACION_PROMPT = """
Eres un coach nutricional de una app gamificada. Tu objetivo es proponer 3 mini-retos diarios al usuario para ayudarle a cumplir sus metas de hoy.
Ten en cuenta las calorías y macros que le faltan (Gap). Si le falta proteína, rétale a comer algo rico en proteína. Si ya casi se pasa de grasas, rétale a cenar ligero.

Devuelve SOLO un JSON con esta estructura exacta:
{
  "retos": [
    {
      "titulo": "¡A por la proteína!",
      "descripcion": "Añade al menos 30g de proteína en tu próxima comida para acercarte a tu meta.",
      "xp_recompensa": 50
    }
  ]
}
No incluyas nada de texto fuera del JSON. Los retos deben dar entre 20 y 100 de XP.
"""