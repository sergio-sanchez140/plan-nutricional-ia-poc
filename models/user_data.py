from pydantic import BaseModel, EmailStr, Field, field_validator
from .enums import ActivityLevel, Goal, Gender


class UserCreate(BaseModel):
    nombre: str = Field(
        ..., 
        min_length=2, 
        max_length=50, 
        pattern="^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$",
        description="Nombre del usuario, solo letras y espacios."
    )
    email: EmailStr

    @field_validator("nombre")
    def normalize_nombre(cls, v: str) -> str:
        return v.strip().title()  # elimina espacios extras y capitaliza


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
