from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import health_routes, db_routes, menu_routes
from db.init_db import init_db
from routes import gamification_routes

app = FastAPI(title="Plan Nutricional IA POC")

# 🔹 Configurar CORS
origins = [
    "http://localhost:5500",  # Flutter Web local
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "https://tu-dominio.com",  # producción
    # "*"  # ⚠️ solo para pruebas, permite todos los orígenes
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # quién puede llamar al backend
    allow_credentials=True,
    allow_methods=["*"],        # GET, POST, PUT, DELETE...
    allow_headers=["*"],        # Authorization, Content-Type...
)

# Inicializar la base de datos al arrancar
@app.on_event("startup")
def on_startup():
    init_db()

# Registrar routers
app.include_router(db_routes.router, prefix="/db", tags=["Users"])
app.include_router(health_routes.router, prefix="/health", tags=["Health"])
app.include_router(menu_routes.router, prefix="/ai", tags=["AI Menus"])  # Menús IA
app.include_router(gamification_routes.router, tags=["Gamification"])