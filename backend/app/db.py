"""
Capa de acceso a datos.

Encapsula la comunicacion con la base de datos PostgreSQL alojada en Supabase
a traves de su API REST (PostgREST). Todas las consultas del backend pasan por
aqui, de modo que la clave secreta nunca sale del servidor.
"""
import requests

from . import config


class ErrorBaseDatos(Exception):
    """Error al comunicarse con la base de datos."""


def _headers(extra: dict | None = None) -> dict:
    cabeceras = {
        "apikey": config.SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        cabeceras.update(extra)
    return cabeceras


def _url(tabla: str) -> str:
    return f"{config.SUPABASE_URL}/rest/v1/{tabla}"


def _procesar(respuesta: requests.Response):
    if respuesta.status_code >= 400:
        raise ErrorBaseDatos(
            f"HTTP {respuesta.status_code} - {respuesta.text[:300]}"
        )
    if not respuesta.text.strip():
        return []
    return respuesta.json()


def seleccionar(tabla: str, params: dict | None = None) -> list:
    """SELECT sobre una tabla o vista. `params` acepta filtros PostgREST."""
    respuesta = requests.get(
        _url(tabla), headers=_headers(), params=params or {}, timeout=30
    )
    return _procesar(respuesta)


def insertar(tabla: str, registros: list | dict) -> list:
    """INSERT de uno o varios registros."""
    respuesta = requests.post(
        _url(tabla),
        headers=_headers({"Prefer": "return=representation"}),
        json=registros,
        timeout=30,
    )
    return _procesar(respuesta)


def upsert(tabla: str, registros: list | dict, on_conflict: str) -> list:
    """
    INSERT ... ON CONFLICT DO UPDATE.

    Lo usa el ETL para que recargar un mismo periodo actualice el resultado
    en lugar de duplicarlo.
    """
    respuesta = requests.post(
        _url(tabla),
        headers=_headers(
            {"Prefer": "return=representation,resolution=merge-duplicates"}
        ),
        params={"on_conflict": on_conflict},
        json=registros,
        timeout=30,
    )
    return _procesar(respuesta)


def eliminar_todo(tabla: str) -> None:
    """
    Vacia una tabla completa.

    PostgREST exige un filtro en toda operacion DELETE, por lo que se usa una
    condicion que satisfacen todas las filas.
    """
    clave = {
        "resultado_kpi": "id_resultado",
        "meta_kpi": "id_meta",
        "indicador_kpi": "id_kpi",
        "proceso_ti": "id_proceso",
        "fuente_dato": "id_fuente",
        "usuario": "id_usuario",
        "rol": "id_rol",
        "notificacion": "id_notificacion",
        "incidencia": "id_incidencia",
    }.get(tabla, "id")

    respuesta = requests.delete(
        _url(tabla), headers=_headers(), params={clave: "gt.0"}, timeout=60
    )
    _procesar(respuesta)


def ejecutar_sql(sentencias: str) -> None:
    """
    Ejecuta SQL arbitrario mediante la funcion RPC `ejecutar_sql`.

    Solo se utiliza en la inicializacion de la base de datos; requiere que la
    funcion exista en el esquema public (ver backend/sql/00_funcion_rpc.sql).
    """
    respuesta = requests.post(
        f"{config.SUPABASE_URL}/rest/v1/rpc/ejecutar_sql",
        headers=_headers(),
        json={"consulta": sentencias},
        timeout=120,
    )
    _procesar(respuesta)


def probar_conexion() -> dict:
    """Verifica que la base responda y reporta si el esquema ya esta creado."""
    try:
        respuesta = requests.get(
            f"{config.SUPABASE_URL}/rest/v1/",
            headers=_headers(),
            timeout=15,
        )
    except requests.RequestException as exc:
        return {"conectado": False, "detalle": str(exc)}

    if respuesta.status_code != 200:
        return {
            "conectado": False,
            "detalle": f"HTTP {respuesta.status_code} - {respuesta.text[:200]}",
        }

    try:
        seleccionar("indicador_kpi", {"select": "id_kpi", "limit": 1})
        esquema = True
    except ErrorBaseDatos:
        esquema = False

    return {
        "conectado": True,
        "esquema_creado": esquema,
        "url": config.SUPABASE_URL,
    }
