import datetime
from typing import Dict, Any, List, Literal
from pydantic import BaseModel

class NutritionPlanCreate(BaseModel):
    tipo: str
    calorias: float
    macros: Dict[str, float]
    menu: Dict[str, Any]  # dict de comidas

class NutritionPlanRead(BaseModel):
    id: int
    user_id: int
    tipo: str
    calorias: float
    macros: Dict[str, float]
    menu: Dict[str, Any]
    created_at: datetime.datetime

    model_config = {
        "from_attributes": True,   # reemplaza orm_mode
        "arbitrary_types_allowed": True  # permite datetime sin error
    }

class MenuTipoRequest(BaseModel):
    tipo: Literal["diario", "semanal", "mensual"]

class ReplaceMealRequest(BaseModel):
    meal_type: str
    macros: Dict[str, int]
    original_foods: List[str] = []