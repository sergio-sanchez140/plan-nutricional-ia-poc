from fastapi import HTTPException

def validar_datos_usuario(user):
    campos_obligatorios = ["edad", "peso", "altura", "nivel_actividad", "objetivo"]

    faltantes = [
        campo for campo in campos_obligatorios
        if getattr(user, campo, None) is None
    ]

    if faltantes:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PROFILE_INCOMPLETE",
                "message": "Faltan datos obligatorios para generar el menú",
                "missing_fields": faltantes
            }
        )