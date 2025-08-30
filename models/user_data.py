from pydantic import BaseModel
from .enums import ActivityLevel, Goal, Gender

class UserData(BaseModel):
    edad: int
    peso: float       # kg
    altura: float     # cm
    genero: Gender
    nivel_actividad: ActivityLevel
    objetivo: Goal
    preferencias: list[str] = []
    restricciones: list[str] = []
