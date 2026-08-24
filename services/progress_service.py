from datetime import date, timedelta
from sqlalchemy.orm import Session
from models.db_models import User
from services.nutrition import get_total_intake_for_date, get_user_plan_by_type

def obtener_historial_30_dias(db: Session, current_user: User) -> dict:
    hoy = date.today()
    plan_actual = get_user_plan_by_type(db, current_user, "diario")
    
    # Meta calórica. Si el usuario aún no tiene plan, usamos 2000 por defecto
    meta_calorias = plan_actual.calorias if plan_actual else 2000
    
    historial = []
    dias_perfectos = 0
    
    # Iteramos desde hace 29 días hasta hoy (30 días en total)
    # Lo generamos de más antiguo a más reciente para el array
    for i in range(29, -1, -1):
        fecha_iter = hoy - timedelta(days=i)
        
        # 1. Consultar calorías consumidas ese día con nuestra función existente
        consumed_cal, _ = get_total_intake_for_date(db, current_user, fecha_iter)
        
        # 2. Calcular el Status según vuestras reglas
        if consumed_cal == 0:
            status = "empty"
        elif meta_calorias > 0:
            ratio = consumed_cal / meta_calorias
            if 0.90 <= ratio <= 1.10:
                status = "perfect"
                dias_perfectos += 1
            elif 0.80 <= ratio <= 1.20:
                status = "good"
            else:
                status = "missed"
        else:
            status = "empty"
            
        historial.append({
            "fecha": str(fecha_iter),
            "calorias": round(consumed_cal),
            "meta": meta_calorias,
            "status": status
        })

    # Usamos la racha que ya estamos guardando y actualizando en BD en el modelo de usuario
    racha_actual = current_user.racha_dias if current_user.racha_dias else 0

    return {
        "racha_actual": racha_actual,
        "dias_perfectos": dias_perfectos,
        "historial": historial
    }