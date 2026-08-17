import requests
from core.config import settings

# Foto genérica por si algo falla o Groq se inventa un término rarísimo
FALLBACK_IMAGE = "https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg"

def get_food_image_url(search_term: str) -> str:
    """Busca una imagen en Pexels y devuelve la URL (Medium size)."""
    if not search_term or not settings.PEXELS_API_KEY:
        return FALLBACK_IMAGE

    url = f"https://api.pexels.com/v1/search?query={search_term}&per_page=1&orientation=landscape"
    headers = {"Authorization": settings.PEXELS_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("photos") and len(data["photos"]) > 0:
                # 'medium' es perfecto para móviles (suele ser ~800px)
                return data["photos"][0]["src"]["medium"]
    except Exception as e:
        print(f"[WARN PEXELS] Error buscando imagen para '{search_term}': {str(e)}")
    
    return FALLBACK_IMAGE