from fastapi import FastAPI
from routes import nutrition_routes, health_routes

app = FastAPI()

# Registrar routers
app.include_router(nutrition_routes.router)
app.include_router(health_routes.router)