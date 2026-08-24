from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.db_models import User
from db.database import get_db
from utils.auth_utils import get_current_user
from services.progress_service import obtener_historial_30_dias # Ajusta el import

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