from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from models.db_models import User, Meal, NutritionPlan, UserIntake
from models.plan_schemas import IntakeSchema
from services.groq_client import generate_menu_with_groq
from services.nutrition import get_total_intake_for_date, get_user_plan_by_type
from core.prompts import ANALISIS_TEXTO_PROMPT, RECALCULO_PARCIAL_PROMPT
from services.pexels_client import get_food_image_url

# Diccionario de horas límite para cada turno
TURNOS_HORAS = {"desayuno": 11, "almuerzo": 13, "comida": 16, "merienda": 19, "cena": 23}

from datetime import datetime, date # Añade datetime a tus imports arriba

def obtener_ingestas_hoy(db: Session, current_user: User) -> dict:
    hoy = date.today()
    hora_actual = datetime.now().hour
    TURNOS_HORAS = {"desayuno": 11, "almuerzo": 13, "comida": 16, "merienda": 19, "cena": 23}
    
    consumed_cal, consumed_macros = get_total_intake_for_date(db, current_user, hoy)
    
    plan_actual = get_user_plan_by_type(db, current_user, "diario")
    comidas_completadas = []
    turnos_pendientes = [] # 🔥 Nueva lista para el Front-end
    
    if plan_actual:
        todas_las_comidas = db.query(Meal).filter(Meal.plan_id == plan_actual.id, Meal.dia == 1).all()
        
        for meal in todas_las_comidas:
            if meal.completed:
                comidas_completadas.append(meal)
            else:
                # Si no está completada y ya pasó la hora, es un turno pendiente
                hora_limite = TURNOS_HORAS.get(meal.turno, 23)
                if hora_actual > hora_limite:
                    turnos_pendientes.append({
                        "id_comida": meal.id,
                        "turno": meal.turno,
                        "nombre": meal.nombre
                    })

    for meal in comidas_completadas:
        consumed_cal += (meal.calorias or 0)
        m = meal.macros or {}
        consumed_macros["carbohidratos_g"] += m.get("carbohidratos_g", 0)
        consumed_macros["proteinas_g"] += m.get("proteinas_g", 0)
        consumed_macros["grasas_g"] += m.get("grasas_g", 0)
    
    historial = [meal.nombre for meal in comidas_completadas]
    
    return {
        "fecha": str(hoy),
        "calorias_consumidas": consumed_cal,
        "macros_consumidos": consumed_macros,
        "historial": historial,
        "turnos_pendientes": turnos_pendientes # 🔥 Se lo enviamos al Front
    }

def procesar_y_guardar_ingesta(db: Session, current_user: User, data: IntakeSchema) -> dict:
    # ==========================================
    # FASE 1: GUARDAR LA INGESTA LIBRE (IA O TEXTO)
    # ==========================================
    plan_actual = get_user_plan_by_type(db, current_user, "diario")
    if not plan_actual:
        raise ValueError("El usuario necesita generar un plan diario antes de registrar ingestas sueltas.")

    # Caso A: Viene de la Visión IA
    if getattr(data, "nombre_plato", None):
        nombre = data.nombre_plato
        calorias = getattr(data, "calorias", 0)
        
        macros_raw = getattr(data, "macros", {}) or {}
        macros = {
            "carbohidratos_g": macros_raw.get("carbohidratos_g", macros_raw.get("carbohidratos", 0)),
            "proteinas_g": macros_raw.get("proteinas_g", macros_raw.get("proteinas", 0)),
            "grasas_g": macros_raw.get("grasas_g", macros_raw.get("grasas", 0))
        }
        
        ingredientes_raw = getattr(data, "ingredientes", []) or []
        alimentos = []
        for ing in ingredientes_raw:
            if isinstance(ing, str):
                alimentos.append({"nombre": ing, "cantidad_g": None})
            else:
                alimentos.append(ing)
                
    # Caso B: Viene de texto libre (acepta "texto" o "texto_ingesta")
    elif getattr(data, "texto", None) or getattr(data, "texto_ingesta", None):
        nombre = getattr(data, "texto", None) or getattr(data, "texto_ingesta", None)
        calorias = 0
        macros = {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0}
        alimentos = []
    else:
        raise ValueError("Debes enviar 'texto' o 'nombre_plato'")

    # 🔥 CORRECCIÓN: Volvemos a guardarlo como Meal (que es lo que te funcionó antes)
    nueva_comida = Meal(
        plan_id=plan_actual.id,
        dia=1,
        turno="extra",  
        nombre=nombre,
        calorias=calorias,
        macros=macros,
        alimentos=alimentos,
        completed=True, 
        imagen_url="https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg"
    )
    db.add(nueva_comida)
    
    # Actualizar racha diaria
    hoy_str = str(date.today())
    if current_user.ultimo_registro_fecha != hoy_str:
        ayer = str(date.today() - timedelta(days=1))
        current_user.racha_dias = (current_user.racha_dias + 1) if current_user.ultimo_registro_fecha == ayer else 1
        current_user.ultimo_registro_fecha = hoy_str

    db.commit()

    # ==========================================
    # FASE 2: RECÁLCULO DINÁMICO (CHECKLIST)
    # ==========================================
    plan_actual = get_user_plan_by_type(db, current_user, "diario")

    # 🔥 CORRECCIÓN: Lo leemos con getattr para que NUNCA crashee aunque falte en el esquema
    resoluciones = getattr(data, "resolucion_pendientes", None)

    if plan_actual and resoluciones is not None:
        try:
            hora_actual = datetime.now().hour
            comidas_hoy = db.query(Meal).filter(Meal.plan_id == plan_actual.id, Meal.dia == 1).all()
            turnos_futuros = []

            # 🔥 CORRECCIÓN 2: Lo hacemos compatible tanto si Pydantic devuelve objetos como diccionarios
            dict_resoluciones = {}
            for r in resoluciones:
                turno = getattr(r, "turno", r.get("turno") if isinstance(r, dict) else None)
                estado = getattr(r, "estado", r.get("estado") if isinstance(r, dict) else None)
                if turno and estado:
                    dict_resoluciones[turno] = estado

            # 2.1 Resolver Fantasmas con precisión láser
            for meal in comidas_hoy:
                hora_limite = TURNOS_HORAS.get(meal.turno, 23)
                es_pasado = hora_actual > hora_limite

                if es_pasado and not meal.completed:
                    estado_elegido = dict_resoluciones.get(meal.turno)
                    
                    if estado_elegido == "completado":
                        meal.completed = True
                    elif estado_elegido == "saltado":
                        meal.calorias = 0
                        meal.macros = {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0}
                        meal.completed = True
                
                elif not es_pasado and not meal.completed:
                    turnos_futuros.append(meal.turno)
            
            db.commit() # Guardamos los fantasmas resueltos
            
            # 2.2 Calcular el nuevo Gap real (Incluye la hamburguesa que acabamos de guardar en Fase 1)
            consumed_cal, consumed_macros = get_total_intake_for_date(db, current_user, date.today())
            
            gap_cal = plan_actual.calorias - consumed_cal
            gap_mac = {
                "carbohidratos": max(0, plan_actual.macros.get("carbohidratos_g", 0) - consumed_macros.get("carbohidratos_g", 0)),
                "proteinas": max(0, plan_actual.macros.get("proteinas_g", 0) - consumed_macros.get("proteinas_g", 0)),
                "grasas": max(0, plan_actual.macros.get("grasas_g", 0) - consumed_macros.get("grasas_g", 0))
            }

            # 2.3 Llamar a la IA si hay presupuesto y turnos
            if turnos_futuros and gap_cal > 50:
                prompt = RECALCULO_PARCIAL_PROMPT.replace("{turnos_futuros}", str(turnos_futuros))
                
                nuevas_comidas = generate_menu_with_groq(
                    gap_cal, gap_mac, current_user.preferencias or [], current_user.restricciones or [], prompt
                )

                # 2.4 Borrar futuro obsoleto y meter el nuevo
                db.query(Meal).filter(Meal.plan_id == plan_actual.id, Meal.turno.in_(turnos_futuros), Meal.completed == False).delete(synchronize_session=False)
                
                for comida in nuevas_comidas:
                    foto_url = get_food_image_url(comida.get("image_search_term", "healthy meal"))
                    nueva_meal = Meal(
                        plan_id=plan_actual.id, dia=1, turno=comida.get("turno", turnos_futuros[0]),
                        nombre=comida.get("nombre", "Comida Ajustada"), alimentos=comida.get("ingredientes", []),
                        macros=comida.get("macros", {"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0}),
                        calorias=comida.get("calorias", 0), imagen_url=foto_url, completed=False
                    )
                    db.add(nueva_meal)
                db.commit()
                
                return {"ok": True, "message": "Ingesta registrada y plan restante ajustado inteligentemente"}
            
            elif turnos_futuros and gap_cal <= 50:
                # Se pasó de calorías, le borramos el resto del día para no tentarle.
                db.query(Meal).filter(Meal.plan_id == plan_actual.id, Meal.turno.in_(turnos_futuros)).delete(synchronize_session=False)
                db.commit()
                return {"ok": True, "message": "Ingesta registrada. Has alcanzado tu límite diario, menú restante cancelado."}

        except Exception as e:
            # Fallback defensivo: Si la IA falla por red o token limits, la ingesta original ya está a salvo.
            print(f"Error en recálculo IA: {e}")
            return {"ok": True, "message": "Ingesta registrada, pero el servicio de recálculo no está disponible."}

    return {"ok": True, "message": "Ingesta registrada correctamente en el historial"}

def analizar_ingesta_texto(texto: str) -> dict:
    if not texto.strip():
        raise ValueError("El texto de la ingesta no puede estar vacío")
        
    prompt = ANALISIS_TEXTO_PROMPT.replace("{texto}", texto)
    
    # Aquí llamas a Groq. Asumo que tienes un cliente configurado. 
    # Ejemplo genérico de cómo debería ser la llamada:
    # respuesta_json = tu_funcion_que_llama_a_groq(prompt)
    
    # ⚠️ REEMPLAZA ESTO por tu llamada real a Groq/Gemini
    respuesta_json = llamar_a_groq_json(prompt) 
    
    return respuesta_json