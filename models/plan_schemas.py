from typing import Dict, Any
from pydantic import BaseModel

class NutritionPlanCreate(BaseModel):
    user_id: int
    tipo: str
    calorias: float
    macros: Dict[str, float]
    menu: Dict[str, Any]