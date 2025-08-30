from fastapi import APIRouter
from core.config import settings

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "API de Planificación Nutricional con Groq AI"}

@router.get("/health")
async def health_check():
    return {"status": "healthy", "model": settings.GROQ_MODEL}