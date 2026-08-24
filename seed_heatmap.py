import sys
import os
import random
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.db_models import User, UserIntake, NutritionPlan

# Conexión directa a tu BD real
SQLALCHEMY_DATABASE_URL = "sqlite:///./db/data/nutrition.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_heatmap_data():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("❌ No hay usuarios en la base de datos.")
            return

        plan_actual = db.query(NutritionPlan).filter(
            NutritionPlan.user_id == user.id, 
            NutritionPlan.tipo == "diario"
        ).first()
        
        meta_calorias = plan_actual.calorias if plan_actual else 2000
        hoy = date.today()

        print(f"🚀 Inyectando datos para el usuario {user.email} (Meta: {meta_calorias} kcal)")

        for i in range(30):
            fecha_iter = hoy - timedelta(days=i)
            probabilidad = random.random()
            
            if probabilidad < 0.15:
                calorias_dia = 0
            elif probabilidad < 0.40:
                calorias_dia = meta_calorias * random.choice([0.6, 1.4]) 
            elif probabilidad < 0.70:
                calorias_dia = meta_calorias * random.uniform(0.8, 1.2)
            else:
                calorias_dia = meta_calorias * random.uniform(0.9, 1.1)

            calorias_dia = int(calorias_dia)

            if calorias_dia > 0:
                # CREAMOS UN USERINTAKE, NO UN MEAL
                nueva_ingesta = UserIntake(
                    user_id=user.id,
                    fecha=fecha_iter,
                    calorias=calorias_dia,
                    macros={"carbohidratos_g": 0, "proteinas_g": 0, "grasas_g": 0},
                    alimentos=[{"nombre": f"Simulación del {fecha_iter.strftime('%d/%m')}", "cantidad_g": 100}]
                )
                db.add(nueva_ingesta)
                print(f"✅ Creado día {fecha_iter}: {calorias_dia} kcal")
            else:
                print(f"⬜ Día {fecha_iter}: Vacío (0 kcal)")

        db.commit()
        print("\n🎉 ¡Historial de 30 días inyectado correctamente!")

    except Exception as e:
        print(f"❌ Error al inyectar datos: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_heatmap_data()