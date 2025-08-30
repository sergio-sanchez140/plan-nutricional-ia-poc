from enum import Enum

class ActivityLevel(str, Enum):
    sedentary = "sedentario"
    light = "ligero"
    moderate = "moderado"
    active = "activo"
    very_active = "muy_activo"

class Goal(str, Enum):
    lose = "perder"
    maintain = "mantener"
    gain = "ganar"

class Gender(str, Enum):
    male = "hombre"
    female = "mujer"