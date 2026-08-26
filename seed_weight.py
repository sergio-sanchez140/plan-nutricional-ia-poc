import sys
import os
import random
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.db_models import User, WeightHistory

SQLALCHEMY_DATABASE_URL = "sqlite:///./db/data/nutrition.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_weight_data():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("❌ No hay usuarios en la base de datos.")
            return

        print(f"🚀 Inyectando historial de peso para {user.email}...")

        peso_inicial = 92.5
        peso_actual_simulado = peso_inicial
        hoy = date.today()

        # Generar un registro por semana (aprox) durante los últimos 90 días
        for i in range(90, -1, -7):
            fecha_iter = hoy - timedelta(days=i)
            
            # Fluctuación realista: baja entre 0.2 y 0.8 kg por semana, a veces sube un poco
            variacion = random.uniform(-0.8, 0.2)
            peso_actual_simulado += variacion
            peso_actual_simulado = round(peso_actual_simulado, 1)

            nuevo_registro = WeightHistory(
                user_id=user.id,
                fecha=fecha_iter,
                peso=peso_actual_simulado
            )
            db.add(nuevo_registro)
            print(f"✅ Registrado {fecha_iter}: {peso_actual_simulado} kg")

        # Actualizamos el perfil del usuario con el último peso
        user.peso = peso_actual_simulado
        db.commit()
        
        print("\n🎉 ¡Historial de peso de 90 días inyectado correctamente!")

    except Exception as e:
        print(f"❌ Error al inyectar datos: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_weight_data()