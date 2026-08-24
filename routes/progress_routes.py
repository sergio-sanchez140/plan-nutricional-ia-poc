from fastapi import APIRouter, Path, Depends, HTTPException
from sqlalchemy.orm import Session
from models.db_models import User
from db.database import get_db
from utils.auth_utils import get_current_user
from services.progress_service import obtener_historial_30_dias, obtener_detalle_dia

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