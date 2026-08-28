from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Rutas
from routes import health_routes, db_routes, menu_routes, gamification_routes
from routes.progress_routes import router as progress_router
from routes.notification_routes import router as notification_router
from db.init_db import init_db

# 🌟 ARQUITECTURA MODERNA: Lifespan sustituye a @app.on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lógica de ARRANQUE
    print("🚀 Inicializando Base de Datos...")
    init_db()
    yield
    # Lógica de APAGADO (Cerrar conexiones a Redis, pools de BD, etc.)
    print("💤 Apagando servidor de forma segura...")

app = FastAPI(title="Plan Nutricional IA POC", lifespan=lifespan)

# 🔹 Configurar CORS (Optimizado para Desarrollo Móvil y Web)
origins = [
    "http://localhost:5500",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "https://tu-dominio.com",
    "*"  # ⚠️ Activado para permitir emuladores Android (10.0.2.2) y dispositivos físicos en red local. Quitar en Producción.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      
    allow_credentials=True,
    allow_methods=["*"],        
    allow_headers=["*"],        
)

# 🔹 Registrar routers
app.include_router(db_routes.router, prefix="/db", tags=["Users"])
app.include_router(health_routes.router, prefix="/health", tags=["Health"])

# 🤖 Agrupación Lógica del CORE (Todo lo que usa IA o Lógica de Negocio bajo /ai)
app.include_router(menu_routes.router, prefix="/ai", tags=["AI Menus"]) 
app.include_router(progress_router, prefix="/ai", tags=["Progress"])
app.include_router(notification_router, prefix="/ai", tags=["Notification"])

# 🎮 Gamificación (No le pusiste prefijo, lo dejamos en la raíz, ej: /leaderboard)
app.include_router(gamification_routes.router, tags=["Gamification"])