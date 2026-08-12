import datetime
from typing import Dict, Any, List, Literal
from pydantic import BaseModel

# 🔹 Schema para cada comida
class MealRead(BaseModel):
    id: int
    plan_id: int
    dia: int      # <-- NUEVO
    turno: str    # <-- NUEVO
    nombre: str
    macros: Dict[str, float]
    calorias: float
    completed: bool

    model_config = {
        "from_attributes": True
    }

# 🔹 Schema para crear plan (input)
class NutritionPlanCreate(BaseModel):
    tipo: str
    calorias: float
    macros: Dict[str, float]

# 🔹 Schema para leer plan (output), incluyendo comidas
class NutritionPlanRead(BaseModel):
    id: int
    user_id: int
    tipo: str
    calorias: float
    macros: Dict[str, float]
    created_at: datetime.datetime
    # 🔹 Ahora acepta tanto {"desayuno": [...]} como {"1": {"desayuno": [...]}}
    menu: Dict[str, Any] = {} 

    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True
    }

# 🔹 Schema para solicitud de tipo de menú
class MenuTipoRequest(BaseModel):
    tipo: Literal["diario", "semanal", "mensual"]

# 🔹 Schema para reemplazar comida
class ReplaceMealRequest(BaseModel):
    nombre: str
    macros: Dict[str, int]
    calorias: int
    original_foods: List[str] = []