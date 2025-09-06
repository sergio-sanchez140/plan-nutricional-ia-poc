from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from db.database import Base

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
    menu = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="plans")
