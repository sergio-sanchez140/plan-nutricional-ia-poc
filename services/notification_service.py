from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from models.db_models import User, Meal
from services.nutrition import get_user_plan_by_type

# Diccionario de horas ideales de notificación (30 mins antes de comer)
TURNOS_NOTIFICACION = {
    "desayuno": {"hora": 8, "minuto": 30},
    "almuerzo": {"hora": 11, "minuto": 0},  # Snack media mañana
    "comida": {"hora": 13, "minuto": 30},
    "merienda": {"hora": 17, "minuto": 30},
    "cena": {"hora": 20, "minuto": 30}
}

def _generar_id_notificacion(fecha: date, base_id: int) -> int:
    """ Genera un ID numérico único (requerido por Android/iOS local push) """
    fecha_str = fecha.strftime("%Y%m%d")
    return int(f"{fecha_str}{base_id}")

def generar_guion_notificaciones(db: Session, current_user: User) -> dict:
    hoy = date.today()
    manana = hoy + timedelta(days=1)
    ahora = datetime.now()
    
    plan_actual = get_user_plan_by_type(db, current_user, "diario")
    notificaciones = []

    if plan_actual:
        comidas = db.query(Meal).filter(Meal.plan_id == plan_actual.id, Meal.dia == 1).all()
        
        # Generamos el guion para HOY y MAÑANA (para asegurar que tengan avisos si no abren la app mañana)
        for fecha_target in [hoy, manana]:
            for meal in comidas:
                conf = TURNOS_NOTIFICACION.get(meal.turno.lower())
                if not conf:
                    continue
                
                hora_programada = datetime(
                    fecha_target.year, fecha_target.month, fecha_target.day, 
                    conf["hora"], conf["minuto"]
                )

                # Si es para hoy, y la hora ya pasó, no la programamos
                if fecha_target == hoy and hora_programada < ahora:
                    continue
                
                # Plantillas dinámicas de texto
                if meal.turno == "desayuno":
                    titulo = "🌞 ¡Buenos días! Tu desayuno está listo"
                    cuerpo = f"Hoy toca: {meal.nombre}. ¡Empieza el día con energía!"
                elif meal.turno == "cena":
                    titulo = "¿Qué toca para cenar? 🌙"
                    cuerpo = f"Tu {meal.nombre} te espera. Abre tu plan."
                else:
                    titulo = f"🍽️ ¡Hora de tu {meal.turno}!"
                    cuerpo = f"Toca {meal.nombre}. No olvides registrarlo."

                notificaciones.append({
                    "id_notificacion": _generar_id_notificacion(fecha_target, meal.id),
                    "id_referencia": f"meal_{meal.id}_{fecha_target.strftime('%Y%m%d')}",
                    "tipo": "recordatorio_comida",
                    "titulo": titulo,
                    "cuerpo": cuerpo,
                    "hora_programada": hora_programada.isoformat(),
                    "requiere_cancelacion_al_completar": True
                })

    # === ALERTA DE RACHA (Gamificación) ===
    # Programamos a las 22:30 si la racha > 0
    for fecha_target in [hoy, manana]:
        hora_racha = datetime(fecha_target.year, fecha_target.month, fecha_target.day, 22, 30)
        
        if fecha_target == hoy and hora_racha < ahora:
            continue

        racha = current_user.racha_dias or 0
        if racha > 0:
            titulo_racha = f"¡No pierdas tu racha de {racha} días! 🔥"
            cuerpo_racha = "Solo te falta registrar tu última comida para mantener el fuego vivo."
        else:
            titulo_racha = "¡Empieza tu racha hoy! 🔥"
            cuerpo_racha = "Registra tus comidas de hoy y da el primer paso hacia tu meta."

        notificaciones.append({
            "id_notificacion": _generar_id_notificacion(fecha_target, 999), # 999 = ID reservado para racha
            "id_referencia": f"streak_warning_{fecha_target.strftime('%Y%m%d')}",
            "tipo": "alerta_racha",
            "titulo": titulo_racha,
            "cuerpo": cuerpo_racha,
            "hora_programada": hora_racha.isoformat(),
            "requiere_cancelacion_al_completar": False # La racha se maneja distinto en front
        })

    return {
        "sync_timestamp": ahora.isoformat() + "Z",
        "notificaciones_programables": notificaciones
    }