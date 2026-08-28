from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from models.db_models import User
from utils.auth_utils import get_current_user
from services.notification_service import generar_guion_notificaciones

router = APIRouter(tags=["Notifications"])

@router.get("/notifications/schedule")
def get_notification_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Devuelve un guion de notificaciones locales pre-calculadas y personalizadas 
    para que el dispositivo móvil las programe nativamente.
    """
    return generar_guion_notificaciones(db, current_user)