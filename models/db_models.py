from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Date, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import date

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    edad = Column(Integer, nullable=True)
    genero = Column(String, nullable=True)
    peso = Column(Float, nullable=True)
    altura = Column(Float, nullable=True)
    nivel_actividad = Column(String, nullable=True)
    objetivo = Column(String, nullable=True)
    preferencias = Column(JSON, nullable=True)
    restricciones = Column(JSON, nullable=True)

    plans = relationship("NutritionPlan", back_populates="user")


class NutritionPlan(Base):
    __tablename__ = "nutrition_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tipo = Column(String, nullable=False)  # diario, semanal, mensual
    calorias = Column(Float, nullable=False)
    macros = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 🔹 Mapa opcional de turnos a listas de meal_ids
    menu = Column(JSON, nullable=True)  # ej: {"desayuno": [1,2], "comida": [3], "cena": [4,5]}

    user = relationship("User", back_populates="plans")

    meals = relationship(
        "Meal",
        back_populates="plan",
        cascade="all, delete-orphan"
    )

    adjustments = relationship(
        "PlanAdjustment",
        back_populates="plan",
        cascade="all, delete-orphan"
    )


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("nutrition_plans.id"), nullable=False)
    
    # 🔹 NUEVOS CAMPOS PARA EL CALENDARIO 🔹
    dia = Column(Integer, nullable=False, default=1)  # Ej: 1=Lunes, 2=Martes... hasta 7.
    turno = Column(String, nullable=False, default="comida")  # desayuno, comida, cena, snack
    
    nombre = Column(String, nullable=False) # nombre de la comida
    alimentos = Column(JSON, nullable=False) # lista de ingredientes con cantidades
    macros = Column(JSON, nullable=False) # {carbohidratos, proteínas, grasas}
    calorias = Column(Float, nullable=False)
    completed = Column(Boolean, default=False)

    plan = relationship("NutritionPlan", back_populates="meals")


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

class UserIntake(Base):
    __tablename__ = "user_intakes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fecha = Column(Date, nullable=False, default=date.today)  # día de la ingesta
    alimentos = Column(JSON, nullable=False)  # lista de {"nombre": "...", "cantidad_g": ...}
    calorias = Column(Integer, nullable=False, default=0)
    macros = Column(JSON, nullable=False, default={"carbohidratos_g":0,"proteinas_g":0,"grasas_g":0})
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", backref="intakes")


class PlanAdjustment(Base):
    """
    Guarda ajustes aplicados a un plan para una fecha concreta.
    """
    __tablename__ = "plan_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("nutrition_plans.id"), nullable=False)
    fecha = Column(Date, nullable=False, default=date.today)
    adjusted_menu = Column(JSON, nullable=False)  # menú corregido (estructura por turnos con comidas serializadas)
    reason = Column(String, nullable=True)  # opcional: razón / descripción
    created_at = Column(DateTime, server_default=func.now())

    plan = relationship(
        "NutritionPlan",
        back_populates="adjustments"
    )
