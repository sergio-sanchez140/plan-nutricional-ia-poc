# core/gamification_config.py

LEVEL_CONFIG = {
    1: {"titulo": "Novato del Tupper", "xp_requerida": 100},
    2: {"titulo": "Novato del Tupper", "xp_requerida": 250},
    3: {"titulo": "Aprendiz de Macros", "xp_requerida": 500},
    4: {"titulo": "Aprendiz de Macros", "xp_requerida": 1000},
    5: {"titulo": "Chef Metabólico", "xp_requerida": 2000},
    6: {"titulo": "Gurú de la Nutrición", "xp_requerida": 4000},
    7: {"titulo": "Leyenda Absoluta", "xp_requerida": 999999} # Nivel máximo
}

def get_level_info(nivel: int):
    # Si el nivel no existe, devolvemos el máximo
    return LEVEL_CONFIG.get(nivel, LEVEL_CONFIG[max(LEVEL_CONFIG.keys())])