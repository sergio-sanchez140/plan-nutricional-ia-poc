# app/core/prompts.py

# 🔹 Menú diario
MENU_DIARIO_PROMPT = """
Eres un nutricionista experto. Genera un menú diario en formato JSON con las claves: desayuno, comida, cena.
Cada alimento debe incluir la cantidad en gramos, por ejemplo: 200 gr de pechuga, 150 gr de arroz.

Requisitos:
- Calorías diarias: {calories} kcal
- Macronutrientes: {carbs}g carbohidratos, {proteins}g proteínas, {fats}g grasas
- Preferencias: {preferencias}
- Restricciones: {restricciones}

Devuelve SOLO el JSON sin explicaciones adicionales.
"""

# 🔹 Menú semanal
MENU_SEMANAL_PROMPT = """
Eres un nutricionista experto. Genera un plan de comidas para 7 días en formato JSON.
Cada día debe tener desayuno, comida y cena, y cada alimento debe indicar la cantidad en gramos (ejemplo: 200 gr de pechuga, 150 gr de arroz).

Requisitos por día:
- Calorías diarias: {calories} kcal
- Macronutrientes: {carbs}g carbohidratos, {proteins}g proteínas, {fats}g grasas
- Preferencias: {preferencias}
- Restricciones: {restricciones}

Devuelve SOLO el JSON sin explicaciones adicionales.
"""

# 🔹 Menú mensual
MENU_MENSUAL_PROMPT = """
Eres un nutricionista experto. Genera un plan de comidas para 30 días en formato JSON.
Cada día debe tener desayuno, comida y cena, y cada alimento debe incluir la cantidad en gramos (ejemplo: 200 gr de pechuga, 150 gr de arroz).

Requisitos por día:
- Calorías diarias: {calories} kcal
- Macronutrientes: {carbs}g carbohidratos, {proteins}g proteínas, {fats}g grasas
- Preferencias: {preferencias}
- Restricciones: {restricciones}

Devuelve SOLO el JSON sin explicaciones adicionales.
"""

# 🔹 Snack diario
SNACK_DIARIO_PROMPT = """
Eres un nutricionista experto. Genera una lista de snacks saludables para un día, en formato JSON.
Cada snack debe incluir la cantidad en gramos (ejemplo: 30 gr de almendras, 1 manzana 150 gr).

Requisitos:
- Mantener balance de calorías y macronutrientes del día: {calories} kcal
- Preferencias: {preferencias}
- Restricciones: {restricciones}

Devuelve SOLO el JSON sin explicaciones adicionales.
"""

# 🔹 Sustituciones de alimentos
SUSTITUCIONES_PROMPT = """
Eres un nutricionista experto. Dado un alimento {alimento}, genera 3 posibles sustituciones saludables
en el mismo rango calórico y de macronutrientes. Indica la cantidad en gramos de cada sustituto.
Devuelve SOLO el JSON con formato: { "sustituciones": ["200 gr de tofu", "150 gr de pollo", "100 gr de garbanzos"] }
"""