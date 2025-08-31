import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Carpeta data dentro de db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # app/db
DATA_DIR = os.path.join(BASE_DIR, "data")  # ahora será app/db/data
os.makedirs(DATA_DIR, exist_ok=True)  # crea carpeta si no existe

DB_PATH = os.path.join(DATA_DIR, "nutrition.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
