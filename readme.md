# 🥗 Plan Nutricional IA POC

Proyecto **FastAPI + IA** para generar planes nutricionales personalizados, almacenados en una base de datos SQLite.

---

## 🚀 Requisitos

- [Python 3.11+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)

---

## 🔧 Instalación

1. **Clonar el repositorio**

```bash
git clone https://github.com/tu-usuario/plan-nutricional-ia-poc.git
cd plan-nutricional-ia-poc
```

2. **Crear entorno virtual**

En Windows (PowerShell):

```bash
python -m venv venv
venv\Scripts\activate
```

En Linux/Mac:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Instalar dependencias**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Configurar variables de entorno**

Crea un archivo .env en la raíz del proyecto con tu configuración:

```bash
GROQ_API_KEY=tu_api_key
GROQ_API_URL=https://api.groq.com/openai/v1/chat/completions
GROQ_MODEL=llama2-70b-chat
```

5. **Inicializar la base de datos**

La primera vez que inicies la app, FastAPI creará automáticamente la base de datos en app/db/data/nutrition.db.

## ▶️ Ejecución

Levantar el servidor en modo desarrollo:

```bash
uvicorn main:app --reload
```

Si las ejecuciones se mueres, hay que matar uvicorn
```bash
taskkill /F /IM python.exe
uvicorn main:app --reload
```

Abrir en el navegador:

API Docs (Swagger): http://127.0.0.1:8000/docs

ReDoc: http://127.0.0.1:8000/redoc

## 📌 Endpoints principales

GET /health → Estado de la API

POST /db/users → Crear usuario

POST /db/plans → Guardar plan nutricional

POST /nutrition/plan-nutricional-daily → Generar plan diario con IA

## 🗂 Estructura del proyecto
plan-nutricional-ia-poc/
│── main.py
│── requirements.txt
│── .env.example
│── README.md
├── app/
│   ├── core/
│   ├── db/
│   │   ├── data/           # SQLite DB aquí
│   ├── models/
│   ├── routes/
│   └── services/

## 🤝 Contribuir

Haz un fork

Crea una rama (git checkout -b feature/nueva-funcionalidad)

Haz commit (git commit -m 'Agrega nueva funcionalidad')

Push a la rama (git push origin feature/nueva-funcionalidad)

Abre un Pull Request 🚀

## 📄 Licencia