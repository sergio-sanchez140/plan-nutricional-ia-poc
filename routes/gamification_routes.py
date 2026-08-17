from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from models.db_models import User
from models.plan_schemas import ChallengeCompleteRequest
from utils.auth_utils import get_current_user

# Importamos nuestro nuevo servicio
from services.gamification_service import (
    obtener_estado_gamificacion,
    obtener_o_generar_retos_hoy,
    completar_reto_ia
)

router = APIRouter()

@router.get("/gamification/status")
def get_gamification_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Devuelve el nivel, XP, título y racha actual del usuario."""
    return obtener_estado_gamificacion(db, current_user)

@router.get("/ai/challenges")
def get_daily_challenges(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Devuelve los retos de hoy (los genera con IA si no existen aún)."""
    return obtener_o_generar_retos_hoy(db, current_user)

@router.post("/ai/challenges/complete")
def complete_challenge(request: ChallengeCompleteRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Marca un reto como completado, otorga XP y gestiona las subidas de nivel."""
    try:
        return completar_reto_ia(db, current_user, request.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))