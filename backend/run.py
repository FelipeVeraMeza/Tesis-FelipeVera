"""
Punto de entrada del servidor.

Uso:
    python backend/run.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import config
from app.api import crear_app

app = crear_app()

if __name__ == "__main__":
    print("=" * 58)
    print(" Sistema de seguimiento de KPIs - AFP Horizonte")
    print(" Gerencia de Tecnologias de la Informacion")
    print("=" * 58)
    print(f" Servidor:  http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    print(f" Base de datos: {config.SUPABASE_URL}")
    print("=" * 58)
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
