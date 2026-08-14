from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import List

from db.database import get_db
from models.db_models import User, Challenge, NutritionPlan
from utils.auth_utils import get_current_user
from services.nutrition import get_total_intake_for_date, calculate_gap_for_day
from services.groq_client import generate_challenges_with_groq
from pydantic import BaseModel
from datetime import date, timedelta
from core.gamification_config import LEVEL_CONFIG, get_level_info

router = APIRouter()

class ChallengeCompleteRequest(BaseModel):
    id: int

def get_titulo_nivel(nivel: int) -> str:
    titulos = {
        1: "Novato del Tupper",
        2: "Cinturón Blanco en Nutrición",
        3: "Guerrero de los Macros",
        4: "Maestro del Meal Prep",
        5: "Gurú Metabólico"
    }
    return titulos.get(nivel, "Leyenda Nutricional")

@router.get("/gamification/status")
def get_gamification_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    hoy = date.today()
    
    # 💡 TRUCO SENIOR: Evaluación perezosa (Lazy Evaluation) de la racha
    # En lugar de usar un CRON a las 00:00 que consume recursos, 
    # evaluamos si perdió la racha justo en el momento en que pide verla.
    ayer = str(hoy - timedelta(days=1))
    
    if current_user.ultimo_registro_fecha and current_user.ultimo_registro_fecha < ayer:
        # Si su último registro es más antiguo que ayer, perdió la racha
        current_user.racha_dias = 0
        db.commit()

    config_actual = get_level_info(current_user.nivel)
    
    return {
        "nivel": current_user.nivel,
        "titulo": config_actual["titulo"],
        "xp_actual": current_user.xp,
        "xp_siguiente_nivel": config_actual["xp_requerida"],
        "racha_dias": current_user.racha_dias,
        "avatar_url": current_user.avatar_url
    }

@router.get("/ai/challenges")
def get_daily_challenges(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    hoy = str(date.today())
    
    # 1. Mirar si ya hemos generado retos para hoy (para no gastar IA cada vez que recargan la app)
    retos_hoy = db.query(Challenge).filter(
        Challenge.user_id == current_user.id, 
        Challenge.fecha == hoy
    ).all()
    
    if retos_hoy:
        return retos_hoy

    # 2. Si no hay, calculamos el GAP de hoy
    plan = db.query(NutritionPlan).filter(NutritionPlan.user_id == current_user.id).first()
    if not plan:
        # Valores por defecto si no hay plan
        gap_cal = 2000
        gap_mac = {"carbohidratos_g": 200, "proteinas_g": 100, "grasas_g": 60}
    else:
        consumed_cal, consumed_macros = get_total_intake_for_date(db, current_user, date.today())
        gap_dict = calculate_gap_for_day(plan, consumed_cal, consumed_macros)
        gap_cal = gap_dict["calorias"]
        gap_mac = gap_dict["macros"]

    # 3. Pedir a Groq los retos basados en el GAP
    retos_ia = generate_challenges_with_groq(gap_cal, gap_mac)
    
    # 4. Guardar en BD
    nuevos_retos = []
    for reto in retos_ia:
        nuevo = Challenge(
            user_id=current_user.id,
            fecha=hoy,
            titulo=reto["titulo"],
            descripcion=reto["descripcion"],
            xp_recompensa=reto["xp_recompensa"],
            completado=False
        )
        db.add(nuevo)
        nuevos_retos.append(nuevo)
    
    db.commit()
    for reto in nuevos_retos:
        db.refresh(reto)
        
    return nuevos_retos

@router.post("/ai/challenges/complete")
def complete_challenge(
    request: ChallengeCompleteRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    reto = db.query(Challenge).filter(
        Challenge.id == request.id, 
        Challenge.user_id == current_user.id
    ).first()
    
    if not reto:
        raise HTTPException(status_code=404, detail="Reto no encontrado")
    if reto.completado:
        raise HTTPException(status_code=400, detail="Este reto ya fue completado")
        
    reto.completado = True
    current_user.xp += reto.xp_recompensa
    
    # Lógica de subir de nivel acumulativo
    sube_nivel = False
    
    # Usamos un bucle por si gana mucha XP y sube 2 niveles de golpe
    while True:
        config_actual = get_level_info(current_user.nivel)
        if current_user.xp >= config_actual["xp_requerida"] and current_user.nivel < max(LEVEL_CONFIG.keys()):
            current_user.nivel += 1
            sube_nivel = True
        else:
            break
            
    db.commit()
    
    return {
        "ok": True,
        "xp_ganada": reto.xp_recompensa,
        "nuevo_xp_total": current_user.xp,
        "sube_nivel": sube_nivel,
        "nivel_actual": current_user.nivel,
        "nuevo_titulo": get_level_info(current_user.nivel)["titulo"]
    }