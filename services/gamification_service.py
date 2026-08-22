from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List

from models.db_models import User, Challenge, NutritionPlan
from services.nutrition import get_total_intake_for_date, calculate_gap_for_day
from services.groq_client import generate_challenges_with_groq
from core.gamification_config import LEVEL_CONFIG, get_level_info

def obtener_estado_gamificacion(db: Session, current_user: User) -> dict:
    hoy = date.today()
    
    # 💡 Evaluación perezosa (Lazy Evaluation) de la racha
    ayer = str(hoy - timedelta(days=1))
    if current_user.ultimo_registro_fecha and current_user.ultimo_registro_fecha < ayer:
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

def obtener_o_generar_retos_hoy(db: Session, current_user: User) -> List[Challenge]:
    hoy = str(date.today())
    
    # 1. Mirar si ya hemos generado retos para hoy
    retos_hoy = db.query(Challenge).filter(
        Challenge.user_id == current_user.id, 
        Challenge.fecha == hoy
    ).all()
    
    if retos_hoy:
        return retos_hoy

    # 2. Calcular el GAP de hoy
    plan = db.query(NutritionPlan).filter(NutritionPlan.user_id == current_user.id).first()
    if not plan:
        gap_cal = 2000
        gap_mac = {"carbohidratos_g": 200, "proteinas_g": 100, "grasas_g": 60}
    else:
        consumed_cal, consumed_macros = get_total_intake_for_date(db, current_user, date.today())
        gap_dict = calculate_gap_for_day(plan, consumed_cal, consumed_macros)

        gap_cal = gap_dict.get("calorias", gap_dict.get("gap_calorias", 0))
        gap_mac = gap_dict.get("macros", gap_dict.get("gap_macros", {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0}))

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

def completar_reto_ia(db: Session, current_user: User, reto_id: int) -> dict:
    reto = db.query(Challenge).filter(
        Challenge.id == reto_id, 
        Challenge.user_id == current_user.id
    ).first()
    
    if not reto:
        raise ValueError("Reto no encontrado")
    if reto.completado:
        raise ValueError("Este reto ya fue completado")
        
    reto.completado = True
    current_user.xp += reto.xp_recompensa
    
    # Lógica de subir de nivel acumulativo
    sube_nivel = False
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