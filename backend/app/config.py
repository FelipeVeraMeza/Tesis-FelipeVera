"""
Configuracion central del sistema de seguimiento de KPIs.
Carga las variables de entorno desde el archivo .env de la raiz del proyecto.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Raiz del proyecto (dos niveles arriba de este archivo)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")

FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "clave-desarrollo")

# Rutas utiles
FRONTEND_DIR = BASE_DIR / "frontend"
SQL_DIR = BASE_DIR / "backend" / "database" / "migrations"
DATA_DIR = BASE_DIR / "docs" / "plantillas"
UPLOAD_DIR = BASE_DIR / "backend" / "uploads"

# Procesos criticos definidos en el alcance del proyecto
PROCESOS_CRITICOS = ["cambios", "incidentes", "requerimientos", "demanda"]

# ------------------------------------------------------------------
# Servidor de correo para las notificaciones de alerta (RF7)
#
# El envio se activa unicamente cuando SMTP_HOST esta definido en el
# archivo .env. Sin esa configuracion, las notificaciones se registran
# como simuladas, conforme a lo previsto para la etapa de prototipo.
# ------------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PUERTO = int(os.getenv("SMTP_PUERTO", "587"))
SMTP_USUARIO = os.getenv("SMTP_USUARIO", "")
SMTP_CLAVE = os.getenv("SMTP_CLAVE", "")
SMTP_REMITENTE = os.getenv("SMTP_REMITENTE", "kpi@horizonte.cl")
SMTP_TLS = os.getenv("SMTP_TLS", "True").lower() == "true"
SMTP_SSL = os.getenv("SMTP_SSL", "False").lower() == "true"

SMTP_ACTIVO = bool(SMTP_HOST)

# Dominio institucional usado para derivar las casillas de los responsables
DOMINIO_CORREO = os.getenv("DOMINIO_CORREO", "horizonte.cl")
CORREO_GERENCIA = os.getenv("CORREO_GERENCIA", f"gerencia.ti@{DOMINIO_CORREO}")

# ------------------------------------------------------------------
# Conector a Jira
#
# Fuente primaria de los procesos de cambios, incidentes y
# requerimientos segun el levantamiento realizado. La extraccion
# automatica se activa al definir estas variables en el .env.
# ------------------------------------------------------------------
JIRA_URL = os.getenv("JIRA_URL", "")
JIRA_USUARIO = os.getenv("JIRA_USUARIO", "")
JIRA_TOKEN = os.getenv("JIRA_TOKEN", "")

# Proyecto de Jira asociado a cada proceso de TI
JIRA_PROYECTOS = {
    "cambios": os.getenv("JIRA_PROYECTO_CAMBIOS", ""),
    "incidentes": os.getenv("JIRA_PROYECTO_INCIDENTES", ""),
    "requerimientos": os.getenv("JIRA_PROYECTO_REQUERIMIENTOS", ""),
    "demanda": os.getenv("JIRA_PROYECTO_DEMANDA", ""),
}

JIRA_ACTIVO = bool(JIRA_URL and JIRA_USUARIO and JIRA_TOKEN)


def validar_configuracion() -> None:
    """Falla temprano si faltan credenciales, en lugar de dar errores confusos despues."""
    faltantes = [
        nombre
        for nombre, valor in (
            ("SUPABASE_URL", SUPABASE_URL),
            ("SUPABASE_SECRET_KEY", SUPABASE_SECRET_KEY),
        )
        if not valor
    ]
    if faltantes:
        raise RuntimeError(
            "Faltan variables en el archivo .env: " + ", ".join(faltantes)
        )
