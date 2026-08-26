from fastapi import APIRouter, Path, Depends, HTTPException
from sqlalchemy.orm import Session
from models.db_models import User
from db.database import get_db
from utils.auth_utils import get_current_user
# Añade o modifica esta línea en la parte superior:
from services.progress_service import obtener_historial_30_dias, obtener_detalle_dia, obtener_historial_peso, registrar_peso_usuario
from pydantic import BaseModel
from typing import Optional
from fastapi import Query

router = APIRouter()

@router.get("/progress/history/last-30-days")
def get_heatmap_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        resultado = obtener_historial_30_dias(db, current_user)
        return resultado
    except Exception as e:
        print(f"[ERROR BACKEND - Heatmap] {e}")
        raise HTTPException(status_code=500, detail="Error al generar el historial de constancia")

@router.get("/progress/history/{fecha}")
def get_history_detail(
    fecha: str = Path(..., description="Fecha en formato YYYY-MM-DD"), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    try:
        return obtener_detalle_dia(db, current_user, fecha)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[ERROR BACKEND - Drilldown Historial] {e}")
        raise HTTPException(status_code=500, detail="Error al generar el detalle del día")

# Pega esto al final de routes/progress_routes.py:
class WeightRecordSchema(BaseModel):
    peso: float
    fecha: Optional[str] = None # YYYY-MM-DD opcional

@router.get("/progress/weight")
def get_weight_history(
    dias: int = Query(90, description="Días a consultar (ej: 30, 90, 180)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return obtener_historial_peso(db, current_user, dias)

@router.post("/progress/weight")
def add_weight_record(
    data: WeightRecordSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if data.peso <= 0 or data.peso > 300:
        raise HTTPException(status_code=400, detail="Peso inválido.")
    
    from datetime import date
    fecha_obj = date.fromisoformat(data.fecha) if data.fecha else date.today()
    return registrar_peso_usuario(db, current_user, data.peso, fecha_obj)