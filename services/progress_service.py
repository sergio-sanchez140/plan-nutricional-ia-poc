from datetime import date, timedelta
from sqlalchemy.orm import Session
from models.db_models import User, UserIntake, DailyHistory
from services.nutrition import get_total_intake_for_date, get_user_plan_by_type

def _sincronizar_dias_pasados(db: Session, current_user: User, hoy: date):
    """
    LAZY CLOSING: Revisa los últimos 30 días. Si un día ya pasó y no está 
    en el Ledger (DailyHistory), lo calcula por última vez y lo congela.
    """
    plan_actual = get_user_plan_by_type(db, current_user, "diario")
    meta_calorias = plan_actual.calorias if plan_actual else 2000

    for i in range(1, 31):
        fecha_iter = hoy - timedelta(days=i)
        
        # 1. ¿Ya congelamos este día?
        existe = db.query(DailyHistory).filter(
            DailyHistory.user_id == current_user.id,
            DailyHistory.fecha == fecha_iter
        ).first()

        if not existe:
            # 2. No existe. Calculamos totales desde UserIntake
            consumed_cal, macros_totales = get_total_intake_for_date(db, current_user, fecha_iter)
            
            # 3. Calculamos Status inmutable
            if consumed_cal == 0:
                status = "empty"
            elif meta_calorias > 0:
                ratio = consumed_cal / meta_calorias
                if 0.90 <= ratio <= 1.10:
                    status = "perfect"
                elif 0.80 <= ratio <= 1.20:
                    status = "good"
                else:
                    status = "missed"
            else:
                status = "empty"

            # 4. Empaquetamos todo lo que comió ese día en JSON
            ingestas = db.query(UserIntake).filter(
                UserIntake.user_id == current_user.id,
                UserIntake.fecha == fecha_iter
            ).all()
            
            comidas_list = []
            for ingesta in ingestas:
                nombre_comida = "Ingesta libre"
                if ingesta.alimentos and isinstance(ingesta.alimentos, list) and len(ingesta.alimentos) > 0:
                    primer_alim = ingesta.alimentos[0]
                    nombre_comida = primer_alim.get("nombre", "Ingesta") if isinstance(primer_alim, dict) else str(primer_alim)
                
                comidas_list.append({
                    "turno": "extra",
                    "nombre": nombre_comida,
                    "calorias": ingesta.calorias or 0
                })

            # 5. Guardamos en el Ledger (Snapshot)
            nuevo_snapshot = DailyHistory(
                user_id=current_user.id,
                fecha=fecha_iter,
                meta_calorias=meta_calorias,
                calorias_consumidas=round(consumed_cal),
                macros_consumidos=macros_totales,
                status=status,
                comidas=comidas_list
            )
            db.add(nuevo_snapshot)
    
    db.commit() # Guardamos todos los snapshots de golpe

def obtener_historial_30_dias(db: Session, current_user: User) -> dict:
    hoy = date.today()
    
    # 1. Ejecutar el cierre automático de días pasados
    _sincronizar_dias_pasados(db, current_user, hoy)

    # 2. Consultar el Ledger (Ultra-rápido, O(1) matemático)
    fecha_limite = hoy - timedelta(days=29)
    historial_bd = db.query(DailyHistory).filter(
        DailyHistory.user_id == current_user.id,
        DailyHistory.fecha >= fecha_limite,
        DailyHistory.fecha < hoy
    ).all()

    # Mapeamos para acceso rápido
    mapa_historial = {h.fecha: h for h in historial_bd}

    historial_result = []
    dias_perfectos = 0
    
    plan_actual = get_user_plan_by_type(db, current_user, "diario")
    meta_hoy = plan_actual.calorias if plan_actual else 2000

    for i in range(29, -1, -1):
        fecha_iter = hoy - timedelta(days=i)
        
        if fecha_iter == hoy:
            # HOY se calcula al vuelo (porque sigue abierto)
            consumed_cal, _ = get_total_intake_for_date(db, current_user, hoy)
            status = "empty"
            if consumed_cal > 0 and meta_hoy > 0:
                ratio = consumed_cal / meta_hoy
                status = "perfect" if 0.90 <= ratio <= 1.10 else "good" if 0.80 <= ratio <= 1.20 else "missed"
                if status == "perfect": dias_perfectos += 1
            
            historial_result.append({
                "fecha": str(fecha_iter), "calorias": round(consumed_cal), "meta": round(meta_hoy), "status": status
            })
        else:
            # PASADO se lee del bloque inmutable
            if fecha_iter in mapa_historial:
                h = mapa_historial[fecha_iter]
                if h.status == "perfect": dias_perfectos += 1
                historial_result.append({
                    "fecha": str(h.fecha), "calorias": h.calorias_consumidas, "meta": h.meta_calorias, "status": h.status
                })
            else:
                historial_result.append({
                    "fecha": str(fecha_iter), "calorias": 0, "meta": meta_hoy, "status": "empty"
                })

    return {
        "racha_actual": current_user.racha_dias or 0,
        "dias_perfectos": dias_perfectos,
        "historial": historial_result
    }

def obtener_detalle_dia(db: Session, current_user: User, fecha_str: str) -> dict:
    try:
        fecha_obj = date.fromisoformat(fecha_str)
    except ValueError:
        raise ValueError("Formato de fecha inválido. Usa YYYY-MM-DD.")

    hoy = date.today()

    # Si es un día del pasado, ¡Leemos directamente del JSON del Ledger!
    if fecha_obj < hoy:
        historial = db.query(DailyHistory).filter(
            DailyHistory.user_id == current_user.id,
            DailyHistory.fecha == fecha_obj
        ).first()

        if historial:
            return {
                "fecha": fecha_str,
                "calorias_consumidas": historial.calorias_consumidas,
                "meta_calorias": historial.meta_calorias,
                "macros": historial.macros_consumidos,
                "comidas": historial.comidas
            }
        # Si no hay historial, devolvemos un día vacío
        return {
            "fecha": fecha_str, "calorias_consumidas": 0, "meta_calorias": 2000,
            "macros": {"proteinas_g": 0, "carbohidratos_g": 0, "grasas_g": 0}, "comidas": []
        }

    # Si es HOY, lo calculamos al vuelo igual que antes
    plan_actual = get_user_plan_by_type(db, current_user, "diario")
    meta_calorias = plan_actual.calorias if plan_actual else 2000
    ingestas = db.query(UserIntake).filter(UserIntake.user_id == current_user.id, UserIntake.fecha == fecha_obj).all()

    calorias_totales = sum(i.calorias or 0 for i in ingestas)
    macros_totales = {"proteinas_g": 0, "carbohidratos_g": 0, "grasas_g": 0}
    comidas_list = []

    for ingesta in ingestas:
        m = ingesta.macros or {}
        macros_totales["carbohidratos_g"] += m.get("carbohidratos_g", 0)
        macros_totales["proteinas_g"] += m.get("proteinas_g", 0)
        macros_totales["grasas_g"] += m.get("grasas_g", 0)

        nombre_comida = "Ingesta libre"
        if ingesta.alimentos and isinstance(ingesta.alimentos, list) and len(ingesta.alimentos) > 0:
            p = ingesta.alimentos[0]
            nombre_comida = p.get("nombre", "Ingesta libre") if isinstance(p, dict) else str(p)

        comidas_list.append({"turno": "extra", "nombre": nombre_comida, "calorias": ingesta.calorias or 0})

    return {
        "fecha": fecha_str,
        "calorias_consumidas": round(calorias_totales),
        "meta_calorias": round(meta_calorias),
        "macros": {k: round(v) for k, v in macros_totales.items()},
        "comidas": comidas_list
    }