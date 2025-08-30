import requests, json
from core.config import settings
from core.prompts import MENU_DIARIO_PROMPT

def generate_menu_with_groq(calories, macros, preferencias, restricciones):
    preferencias_text = ', '.join(preferencias) if preferencias else 'ninguna'
    restricciones_text = ', '.join(restricciones) if restricciones else 'ninguna'

    prompt = MENU_DIARIO_PROMPT.format(
        calories=round(calories),
        carbs=round(macros['carbohidratos_g']),
        proteins=round(macros['proteinas_g']),
        fats=round(macros['grasas_g']),
        preferencias=preferencias_text,
        restricciones=restricciones_text
    )

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Eres un nutricionista experto que genera menús en formato JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload)
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    json_start = content.find('{')
    json_end = content.rfind('}') + 1
    json_str = content[json_start:json_end]

    return json.loads(json_str)
