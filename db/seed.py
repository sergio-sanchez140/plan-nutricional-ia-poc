from sqlalchemy.orm import Session

from models.db_models import User
from utils.auth_utils import hash_password


DEFAULT_USER = {
    "nombre": "Demo User",
    "email": "demo@demo.com",
    "password": "Demo123!"
}


def seed_default_user(db: Session):

    existing_user = db.query(User).filter(
        User.email == DEFAULT_USER["email"]
    ).first()

    if existing_user:
        print("[SEED] Usuario demo ya existe")
        return

    user = User(
        nombre=DEFAULT_USER["nombre"],
        email=DEFAULT_USER["email"],
        hashed_password=hash_password(DEFAULT_USER["password"]),

        edad=30,
        peso=75,
        altura=180,

        genero="male",
        nivel_actividad="moderado",
        objetivo="maintain",

        preferencias=["pollo", "arroz"],
        restricciones=[]
    )

    db.add(user)
    db.commit()

    print("[SEED] Usuario demo creado")