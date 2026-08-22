import requests
import os
from dotenv import load_dotenv

# Carga tu .env
load_dotenv(override=True)
api_key = os.getenv("GROQ_API_KEY")

print("Consultando modelos disponibles en tu cuenta...")
response = requests.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {api_key}"}
)

if response.status_code == 200:
    modelos = [model["id"] for model in response.json()["data"]]
    print("\n✅ ¡ÉXITO! Estos son los modelos que PUEDES usar:")
    for m in modelos:
        print(f" - {m}")
else:
    print(f"❌ Error: {response.text}")