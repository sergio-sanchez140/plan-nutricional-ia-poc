# app/core/prompts.py

# 🔹 Formato estricto para la IA (Objeto con lista para soportar json_mode)
JSON_SCHEMA_INFO = """
Devuelve SOLO un JSON válido. DEBES devolver un OBJETO que contenga una lista llamada "comidas" con TODOS los turnos (desayuno, comida, cena, y snacks si proceden) para alcanzar las calorías objetivo.

Estructura exacta que debes seguir (esto es solo un ejemplo de la estructura, DEBES generar tus propios platos y TODOS los turnos):
{{
  "comidas": [
    {{
      "dia": 1, 
      "turno": "desayuno", 
      "nombre": "Avena con frutas",
      "image_search_term": "oatmeal with fruits",
      "ingredientes": [{{"nombre": "Avena", "cantidad_g": 50}}],
      "macros": {{"carbohidratos_g": 30, "proteinas_g": 10, "grasas_g": 5}},
      "calorias": 200
    }},
    {{
      "dia": 1, 
      "turno": "comida", 
      "nombre": "Pollo a la plancha con arroz",
      "image_search_term": "grilled chicken with rice",
      "ingredientes": [{{"nombre": "Pollo", "cantidad_g": 150}}, {{"nombre": "Arroz", "cantidad_g": 80}}],
      "macros": {{"carbohidratos_g": 60, "proteinas_g": 40, "grasas_g": 10}},
      "calorias": 500
    }}
  ]
}}
IMPORTANTE: No devuelvas solo el ejemplo. Debes generar el menú completo distribuyendo correctamente las calorías.
El campo 'image_search_term' DEBE ser corto (máximo 3-4 palabras) y OBLIGATORIAMENTE EN INGLÉS para que la API de fotos funcione correctamente.
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

Devuelve SOLO un JSON con esta estructura exacta (usar llaves dobles para el esquema):
{{
  "retos": [
    {{
      "titulo": "¡A por la proteína!",
      "descripcion": "Añade al menos 30g de proteína en tu próxima comida para acercarte a tu meta.",
      "xp_recompensa": 50
    }}
  ]
}}
No incluyas nada de texto fuera del JSON. Los retos deben dar entre 20 y 100 de XP.
"""

# 🔹 Prompt para recálculo dinámico parcial
RECALCULO_PARCIAL_PROMPT = """
Eres un nutricionista experto. El usuario se ha desviado de su plan y necesitas recalcular SOLO sus próximas comidas del día para que logre cumplir sus metas nutricionales.

PRESUPUESTO RESTANTE para el resto del día:
- Calorías: {calories} kcal
- Carbohidratos: {carbs}g
- Proteínas: {proteins}g
- Grasas: {fats}g

TURNOS QUE DEBES GENERAR: {turnos_futuros}
Preferencias: {preferencias}
Restricciones: {restricciones}

REGLAS ESTRICTAS:
1. Genera comidas SOLO para los turnos indicados en la lista. Si la lista es ["cena"], solo genera la cena.
2. Distribuye el presupuesto restante equitativamente entre los turnos solicitados.
3. Si el presupuesto restante es muy bajo (ej. menos de 200 kcal), genera opciones extremadamente ligeras (infusiones, gelatinas, un yogur desnatado).

Devuelve SOLO un JSON válido con esta estructura exacta (usar llaves dobles para el esquema):
{{
  "comidas": [
    {{
      "dia": 1, 
      "turno": "cena", 
      "nombre": "Ensalada ligera de atún",
      "image_search_term": "light tuna salad",
      "ingredientes": [{{"nombre": "Lechuga", "cantidad_g": 100}}, {{"nombre": "Atún natural", "cantidad_g": 50}}],
      "macros": {{"carbohidratos_g": 5, "proteinas_g": 12, "grasas_g": 2}},
      "calorias": 86
    }}
  ]
}}
No incluyas NADA de texto fuera del JSON.
"""

ANALISIS_TEXTO_PROMPT = """
Eres un nutricionista experto. El usuario ha escrito lo que ha comido en texto libre.
Tu objetivo es estimar los ingredientes, calorías y macronutrientes aproximados de esa comida basándote en cantidades estándar.

Texto del usuario: "{texto}"

Devuelve SOLO un JSON válido con la siguiente estructura (no incluyas markdown, solo el JSON):
{{
    "nombre_plato": "Nombre del plato resumido (ej: Pizza Barbacoa)",
    "calorias": 650,
    "macros": {{
        "carbohidratos_g": 60,
        "proteinas_g": 25,
        "grasas_g": 30
    }},
    "ingredientes": ["Masa de pizza", "Salsa barbacoa", "Queso", "Carne"]
}}
"""