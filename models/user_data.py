from pydantic import BaseModel, EmailStr, Field, field_validator
from .enums import ActivityLevel, Goal, Gender
from typing import Optional

class UserCreate(BaseModel):
    nombre: str = Field(
        ..., 
        min_length=2, 
        max_length=50, 
        pattern=r"^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$",
        description="Nombre del usuario, solo letras y espacios."
    )
    email: EmailStr
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128, 
        description="Contraseña del usuario (mínimo 8 caracteres)."
    )

    @field_validator("nombre")
    def normalize_nombre(cls, v: str) -> str:
        return v.strip().title()  # elimina espacios extras y capitaliza
    @field_validator("password")
    def validar_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        if not any(c.islower() for c in v):
            raise ValueError("La contraseña debe contener al menos una minúscula")
        if not any(c.isdigit() for c in v):
            raise ValueError("La contraseña debe contener al menos un número")
        if not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for c in v):
            raise ValueError("La contraseña debe contener al menos un símbolo")
        return v

class UserUpdate(BaseModel):
    edad: int | None = Field(
        None, ge=0, le=120, 
        description="Edad en años (0-120)."
    )
    peso: float | None = Field(
        None, ge=20, le=300,
        description="Peso en kilogramos (20-300)."
    )
    altura: float | None = Field(
        None, ge=50, le=250,
        description="Altura en centímetros (50-250)."
    )
    genero: Gender | None = None
    nivel_actividad: ActivityLevel | None = None
    objetivo: Goal | None = None
    preferencias: list[str] | None = Field(
        default_factory=list,
        max_items=10,
        description="Lista de alimentos preferidos, máximo 10."
    )
    restricciones: list[str] | None = Field(
        default_factory=list,
        max_items=10,
        description="Lista de restricciones alimentarias, máximo 10."
    )

    @field_validator("preferencias", "restricciones", mode="before")
    def clean_lists(cls, v):
        if v is None:
            return []
        return list({item.strip().lower() for item in v if item.strip()})


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

class GoogleToken(BaseModel):
    id_token: Optional[str] = None
    access_token: Optional[str] = None