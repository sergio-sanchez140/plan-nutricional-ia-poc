# app/core/prompts.py

MENU_DIARIO_PROMPT = """
Eres un nutricionista experto. Genera un menú diario en formato JSON con las claves: desayuno, comida, cena.

Requisitos:
- Calorías diarias: {calories} kcal
- Macronutrientes: {carbs}g carbohidratos, {proteins}g proteínas, {fats}g grasas
- Preferencias: {preferencias}
- Restricciones: {restricciones}

Devuelve SOLO el JSON sin explicaciones adicionales.
"""
