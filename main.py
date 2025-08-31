from fastapi import FastAPI
from routes import nutrition_routes, health_routes, db_routes
from db.init_db import init_db

app = FastAPI(title="Plan Nutricional IA POC")

# Inicializar la base de datos al arrancar
@app.on_event("startup")
def on_startup():
    init_db()

# Registrar routers
app.include_router(health_routes.router, prefix="", tags=["Health"])
app.include_router(nutrition_routes.router, prefix="/nutrition", tags=["Nutrition"])
app.include_router(db_routes.router, prefix="/db", tags=["Database"])
