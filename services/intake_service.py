from datetime import date, timedelta
from sqlalchemy.orm import Session
from models.db_models import User, Meal, NutritionPlan
from models.plan_schemas import IntakeSchema
from services.nutrition import get_total_intake_for_date

def obtener_ingestas_hoy(db: Session, current_user: User) -> dict:
    hoy = date.today()
    
    # 1. Cálculos totales con tu función existente
    consumed_cal, consumed_macros = get_total_intake_for_date(db, current_user, hoy)
    
    # 2. Rescatar el historial de comidas del plan completadas
    planes = db.query(NutritionPlan).filter(NutritionPlan.user_id == current_user.id).all()
    plan_ids = [p.id for p in planes]
    
    comidas_completadas = db.query(Meal).filter(
        Meal.plan_id.in_(plan_ids),
        Meal.completed == True
    ).all()
    
    historial = [meal.nombre for meal in comidas_completadas]
    
    return {
        "fecha": str(hoy),
        "calorias_consumidas": consumed_cal,
        "macros_consumidos": consumed_macros,
        "historial": historial
    }

def procesar_y_guardar_ingesta(db: Session, current_user: User, data: IntakeSchema) -> dict:
    # Caso A: Viene de la Visión IA (Ya calculado)
    if data.nombre_plato:
        nombre = data.nombre_plato
        calorias = data.calorias
        macros = data.macros or {"proteinas": 0, "carbohidratos": 0, "grasas": 0}
    
    # Caso B: Viene de texto libre
    elif data.texto:
        nombre = data.texto
        calorias = 0
        macros = {}
    else:
        raise ValueError("Faltan datos de la ingesta")

    # Guardar en base de datos
    nueva_comida = Meal(
        user_id=current_user.id,
        nombre=nombre,
        calorias=calorias,
        carbohidratos_g=macros.get("carbohidratos", 0),
        proteinas_g=macros.get("proteinas", 0),
        grasas_g=macros.get("grasas", 0),
        completed=True,
        fecha=str(date.today())
    )
    db.add(nueva_comida)
    
    # Actualizar racha diaria
    hoy_str = str(date.today())
    if current_user.ultimo_registro_fecha != hoy_str:
        ayer = str(date.today() - timedelta(days=1))
        current_user.racha_dias = (current_user.racha_dias + 1) if current_user.ultimo_registro_fecha == ayer else 1
        current_user.ultimo_registro_fecha = hoy_str

    db.commit()
    return {"ok": True, "message": "Ingesta registrada correctamente"}