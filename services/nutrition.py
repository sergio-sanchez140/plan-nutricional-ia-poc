from models.enums import Gender, Goal

def calcular_macros(data):
    # Calcular BMR
    bmr = 10 * data.peso + 6.25 * data.altura - 5 * data.edad
    bmr += 5 if data.genero == Gender.male else -161

    activity_factors = {
        "sedentario": 1.2,
        "ligero": 1.375,
        "moderado": 1.55,
        "activo": 1.725,
        "muy_activo": 1.9
    }
    tdee = bmr * activity_factors.get(data.nivel_actividad.value, 1.2)

    if data.objetivo == Goal.lose:
        calories = tdee - 500
    elif data.objetivo == Goal.gain:
        calories = tdee + 500
    else:
        calories = tdee

    carbs_g = (calories * 0.5) / 4
    protein_g = (calories * 0.25) / 4
    fat_g = (calories * 0.25) / 9

    macros = {
        "carbohidratos_g": round(carbs_g),
        "proteinas_g": round(protein_g),
        "grasas_g": round(fat_g)
    }

    return round(calories), macros
