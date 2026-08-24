import datetime
from typing import Dict, Any, List, Literal, Optional
from pydantic import BaseModel

class ResolucionPendiente(BaseModel):
    turno: str
    estado: Literal["completado", "saltado"]

class IntakeSchema(BaseModel):
    texto: Optional[str] = None
    texto_ingesta: Optional[str] = None
    nombre_plato: Optional[str] = None
    calorias: Optional[int] = 0
    macros: Optional[dict] = None
    ingredientes: Optional[List[str]] = []
    
    # 🔹 Y esto debe estar aquí:
    resolucion_pendientes: Optional[List[ResolucionPendiente]] = None

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
    imagen_url: Optional[str] = None

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

class IntakeSchema(BaseModel):
    texto: Optional[str] = None
    texto_ingesta: Optional[str] = None
    nombre_plato: Optional[str] = None
    calorias: Optional[int] = 0
    macros: Optional[dict] = None
    ingredientes: Optional[List[Any]] = []
    alimentos: Optional[List[Any]] = []
    
    resolucion_pendientes: Optional[List[Any]] = None

class ChallengeCompleteRequest(BaseModel):
    id: int

class TextAnalyzeRequest(BaseModel):
    texto: str