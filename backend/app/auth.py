"""
Modulo de autenticacion y control de acceso (RF4).

Las contrasenas se almacenan cifradas con PBKDF2-SHA256, cumpliendo el
requisito no funcional RNF3. La sesion se maneja mediante un token firmado
que el frontend guarda y envia en cada peticion.
"""
import functools
import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from flask import g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from . import config, db

DURACION_SESION = 8 * 60 * 60  # 8 horas

# Atribuciones de cada perfil, segun los usuarios definidos en el alcance
# del proyecto.
#
#   vista            enfoque del panel que se presenta al iniciar sesion
#   puede_cargar     acceso al modulo de carga de archivos (RF1)
#   puede_notificar  emision de alertas al responsable del proceso (RF7)
#   puede_exportar   descarga de reportes (RF6)
#   ve_todos         acceso al catalogo completo o solo a procesos criticos
PERMISOS = {
    # Vista ejecutiva: estado global de los procesos y cumplimiento de objetivos
    "Gerente": {
        "vista": "ejecutiva",
        "puede_cargar": False,
        "puede_notificar": True,
        "puede_exportar": True,
        "ve_todos": True,
    },
    # Dashboards consolidados: cumplimiento, desviaciones y tendencias
    "Lider": {
        "vista": "consolidada",
        "puede_cargar": False,
        "puede_notificar": True,
        "puede_exportar": True,
        "ve_todos": False,
    },
    # Carga de archivos, validacion de datos y resultados detallados
    "Analista": {
        "vista": "detallada",
        "puede_cargar": True,
        "puede_notificar": False,
        "puede_exportar": True,
        "ve_todos": False,
    },
    # Gestion tecnica del entorno
    "Administrador": {
        "vista": "administracion",
        "puede_cargar": True,
        "puede_notificar": True,
        "puede_exportar": True,
        "ve_todos": True,
    },
}


def cifrar_contrasena(texto_plano: str) -> str:
    return generate_password_hash(texto_plano, method="pbkdf2:sha256")


def _firmar(payload: bytes) -> str:
    firma = hmac.new(
        config.SECRET_KEY.encode(), payload, hashlib.sha256
    ).digest()
    return urlsafe_b64encode(firma).decode().rstrip("=")


def _b64(datos: bytes) -> str:
    return urlsafe_b64encode(datos).decode().rstrip("=")


def _des_b64(texto: str) -> bytes:
    return urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def generar_token(usuario: dict) -> str:
    cuerpo = {
        "id_usuario": usuario["id_usuario"],
        "correo": usuario["correo"],
        "nombre": usuario["nombre_usuario"],
        "rol": usuario["rol"],
        "exp": int(time.time()) + DURACION_SESION,
    }
    payload = json.dumps(cuerpo, separators=(",", ":")).encode()
    return f"{_b64(payload)}.{_firmar(payload)}"


def validar_token(token: str) -> dict | None:
    try:
        parte_payload, firma = token.split(".", 1)
        payload = _des_b64(parte_payload)
    except (ValueError, TypeError):
        return None

    if not hmac.compare_digest(_firmar(payload), firma):
        return None

    datos = json.loads(payload)
    if datos.get("exp", 0) < time.time():
        return None
    return datos


def autenticar(correo: str, contrasena: str) -> dict | None:
    """Valida las credenciales contra la tabla usuario."""
    filas = db.seleccionar(
        "usuario",
        {
            "select": "id_usuario,nombre_usuario,correo,contrasena,activo,rol(nombre_rol)",
            "correo": f"eq.{correo.strip().lower()}",
        },
    )
    if not filas:
        return None

    usuario = filas[0]
    if not usuario.get("activo", True):
        return None
    if not check_password_hash(usuario["contrasena"], contrasena):
        return None

    rol = (usuario.get("rol") or {}).get("nombre_rol", "Analista")
    return {
        "id_usuario": usuario["id_usuario"],
        "nombre_usuario": usuario["nombre_usuario"],
        "correo": usuario["correo"],
        "rol": rol,
        "permisos": PERMISOS.get(rol, PERMISOS["Analista"]),
    }


def requiere_sesion(vista):
    """Decorador que exige un token valido en la cabecera Authorization."""

    @functools.wraps(vista)
    def envoltorio(*args, **kwargs):
        cabecera = request.headers.get("Authorization", "")
        token = cabecera[7:] if cabecera.startswith("Bearer ") else ""
        datos = validar_token(token)
        if not datos:
            return jsonify({"error": "Sesion invalida o expirada"}), 401
        g.usuario = datos
        return vista(*args, **kwargs)

    return envoltorio


def requiere_rol(*roles_permitidos):
    """Decorador que restringe una ruta a determinados roles."""

    def decorador(vista):
        @functools.wraps(vista)
        @requiere_sesion
        def envoltorio(*args, **kwargs):
            if g.usuario.get("rol") not in roles_permitidos:
                return jsonify(
                    {"error": "No tiene permisos para realizar esta accion"}
                ), 403
            return vista(*args, **kwargs)

        return envoltorio

    return decorador
