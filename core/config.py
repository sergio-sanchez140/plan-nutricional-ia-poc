import os
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

class Settings:
    PROJECT_NAME: str = "Plan Nutricional IA POC"
    
    # JWT Auth (Autenticación)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mi_super_clave_secreta_proyecto_ia_2026")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 43200))
    
    # Google Auth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")

    # Groq API (Inteligencia Artificial)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"
    
    # ✅ AQUÍ ESTÁ EL NUEVO MODELO DE VISIÓN:
    GROQ_VISION_MODEL: str = os.getenv("GROQ_VISION_MODEL", "llama-3.2-90b-vision-preview")

    # Base de Datos
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./db/data/nutrition.db")

    # Cloudinary (Subida de imágenes)
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")

settings = Settings()