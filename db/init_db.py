from db.database import Base, engine, SessionLocal
from models import db_models

from db.seed import seed_default_user


def init_db():

    # Crear tablas
    Base.metadata.create_all(bind=engine)

    # Seed usuario demo
    db = SessionLocal()

    try:
        seed_default_user(db)
    finally:
        db.close()


if __name__ == "__main__":
    init_db()