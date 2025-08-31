from pydantic import BaseModel, EmailStr
from .enums import ActivityLevel, Goal, Gender

class UserCreate(BaseModel):
    nombre: str
    email: EmailStr

class UserUpdate(BaseModel):
    edad: int | None = None
    peso: float | None = None       # kg
    altura: float | None = None     # cm
    genero: Gender | None = None
    nivel_actividad: ActivityLevel | None = None
    objetivo: Goal | None = None
    preferencias: list[str] | None = []
    restricciones: list[str] | None = []
