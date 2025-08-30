--------------------To Run-------------------------------

Paso 1: Crear y activar el entorno virtual
bash
# Crear el entorno virtual (si no lo has hecho)
python -m venv venv

# Activar el entorno virtual
# En Linux/Mac:
source venv/bin/activate

# En Windows:
venv\Scripts\activate
Paso 2: Instalar las dependencias necesarias
bash
# Crear archivo requirements.txt con este contenido:
echo "fastapi==0.104.1
uvicorn==0.24.0
requests==2.31.0
python-dotenv==1.0.0
pydantic==2.5.0" > requirements.txt

# Instalar dependencias
pip install -r requirements.txt

pip install fastapi uvicorn python-dotenv requests

uvicorn main:app --reload

