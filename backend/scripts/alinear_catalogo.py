"""
Alineación del catálogo con las fichas técnicas de la memoria.

Los indicadores importados desde la planilla institucional conservan los
nombres y rangos con que fueron registrados internamente, que difieren de la
denominación formal establecida en las Tablas 11 a 14 del documento.

Este script ajusta los once indicadores del alcance —los cuatro procesos
críticos— para que su denominación, meta, unidad y tendencia correspondan
exactamente a lo documentado.

Uso:
    python backend/scripts/alinear_catalogo.py
    python backend/scripts/alinear_catalogo.py --simular
"""
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

from app import config, db  # noqa: E402

ASCENDENTE = 1
DESCENDENTE = 2

# ------------------------------------------------------------------
# Fichas técnicas según las Tablas 11 a 14 de la memoria
#
# La clave identifica al indicador dentro del catálogo importado; los
# valores corresponden a su definición formal en el documento.
# ------------------------------------------------------------------
FICHAS = {
    # ---------- Tabla 11: Gestión de Cambios ----------
    "tasa de aceptacion de cambios": {
        "nombre_kpi": "Tasa de aceptación de cambios",
        "descripcion": "Porcentaje de solicitudes de cambio aceptadas respecto al total ingresado.",
        "formula": "(Cambios aceptados / Cambios solicitados) * 100",
        "unidad_medida": "%",
        "meta": 90,
        "valor_minimo": 0,
        "valor_maximo": 100,
        "tipo_medicion": ASCENDENTE,
        "periodicidad": "Mensual",
    },
    "porcentaje de cambios urgentes": {
        "nombre_kpi": "Cambios urgentes sobre el total",
        "descripcion": "Porcentaje de cambios urgentes ejecutados en el período.",
        "formula": "(Cambios urgentes / Total de cambios) * 100",
        "unidad_medida": "%",
        "meta": 30,
        "valor_minimo": 0,
        "valor_maximo": 100,
        "tipo_medicion": DESCENDENTE,
        "periodicidad": "Mensual",
    },
    "cambios con vuelta atras": {
        "nombre_kpi": "Cambios con vuelta atrás",
        "descripcion": "Porcentaje de cambios revertidos tras su implementación.",
        "formula": "(Cambios revertidos / Cambios implementados) * 100",
        "unidad_medida": "%",
        "meta": 20,
        "valor_minimo": 0,
        "valor_maximo": 100,
        "tipo_medicion": DESCENDENTE,
        "periodicidad": "Mensual",
    },
    "errores en la certificacion": {
        "nombre_kpi": "Cambios con error en certificación",
        "descripcion": "Porcentaje de cambios que presentaron errores durante la fase de certificación.",
        "formula": "(Cambios con error en certificación / Cambios implementados) * 100",
        "unidad_medida": "%",
        "meta": 20,
        "valor_minimo": 0,
        "valor_maximo": 100,
        "tipo_medicion": DESCENDENTE,
        "periodicidad": "Mensual",
    },
    # ---------- Tabla 12: Gestión de Requerimientos ----------
    "cantidad de requerimientos rechazados": {
        "nombre_kpi": "Cantidad de requerimientos rechazados",
        "descripcion": "Número total de requerimientos rechazados en el período.",
        "formula": "Sumatoria de requerimientos rechazados",
        "unidad_medida": "cantidad",
        "meta": 15,
        "valor_minimo": 0,
        "valor_maximo": 60,
        "tipo_medicion": DESCENDENTE,
        "periodicidad": "Mensual",
    },
    "tiempo de resolucion de requerimientos": {
        "nombre_kpi": "Tiempo medio de resolución",
        "descripcion": "Tiempo promedio en que se resuelven los requerimientos.",
        "formula": "(Sumatoria de tiempos de resolución / Requerimientos cerrados)",
        "unidad_medida": "días",
        "meta": 20,
        "valor_minimo": 0,
        "valor_maximo": 36,
        "tipo_medicion": DESCENDENTE,
        "periodicidad": "Mensual",
    },
    "requerimientos dentro de sla": {
        "nombre_kpi": "Porcentaje de resolución dentro de SLA",
        "descripcion": "Proporción de requerimientos resueltos dentro del tiempo comprometido.",
        "formula": "(Requerimientos dentro de SLA / Total de requerimientos cerrados) * 100",
        "unidad_medida": "%",
        "meta": 90,
        "valor_minimo": 0,
        "valor_maximo": 100,
        "tipo_medicion": ASCENDENTE,
        "periodicidad": "Mensual",
    },
    # ---------- Tabla 13: Gestión de Incidentes ----------
    "tiempo resolucion de incidentes": {
        "nombre_kpi": "Tiempo de resolución de incidente",
        "descripcion": "Tiempo promedio para restaurar un servicio afectado.",
        "formula": "(Sumatoria de tiempos de resolución / Incidentes cerrados en el período)",
        "unidad_medida": "horas",
        "meta": 20,
        "valor_minimo": 0,
        "valor_maximo": 30,
        "tipo_medicion": DESCENDENTE,
        "periodicidad": "Mensual",
    },
    "capacidad de cierre de incidentes": {
        "nombre_kpi": "Capacidad de cierre de incidentes",
        "descripcion": "Porcentaje de incidentes cerrados respecto al total de incidentes generados.",
        "formula": "(Incidentes cerrados / Incidentes creados en el período) * 100",
        "unidad_medida": "%",
        "meta": 90,
        "valor_minimo": 0,
        "valor_maximo": 100,
        "tipo_medicion": ASCENDENTE,
        "periodicidad": "Mensual",
    },
    # ---------- Tabla 14: Gestión de Demanda ----------
    "tiempo de resolucion solicitud de demanda": {
        "nombre_kpi": "Tiempo de ciclo de gestión de demanda",
        "descripcion": (
            "Tiempo promedio desde la recepción de la solicitud hasta su "
            "priorización o rechazo."
        ),
        "formula": (
            "(Sumatoria de tiempos de priorización o rechazo / Total de "
            "solicitudes en el período)"
        ),
        "unidad_medida": "días",
        "meta": 15,
        "valor_minimo": 0,
        "valor_maximo": 45,
        "tipo_medicion": DESCENDENTE,
        "periodicidad": "Mensual",
    },
    "solicitudes de demanda evaluadas": {
        "nombre_kpi": "Porcentaje de solicitudes evaluadas dentro de SLA",
        "descripcion": "Proporción de solicitudes priorizadas o rechazadas dentro del plazo comprometido.",
        "formula": "(Solicitudes evaluadas dentro de SLA / Total de solicitudes del período) * 100",
        "unidad_medida": "%",
        "meta": 90,
        "valor_minimo": 0,
        "valor_maximo": 100,
        "tipo_medicion": ASCENDENTE,
        "periodicidad": "Mensual",
    },
}


def normalizar(texto: str) -> str:
    limpio = unicodedata.normalize("NFKD", str(texto or "").lower())
    return "".join(c for c in limpio if not unicodedata.combining(c))


def main() -> None:
    simular = "--simular" in sys.argv

    print("=" * 66)
    print(" Alineación del catálogo con las fichas técnicas")
    print("=" * 66)
    print()

    procesos = db.seleccionar("proceso_ti", {"select": "id_proceso,critico"})
    criticos = {p["id_proceso"] for p in procesos if p.get("critico")}

    indicadores = db.seleccionar(
        "indicador_kpi", {"select": "id_kpi,nombre_kpi,id_proceso", "order": "id_kpi"}
    )
    indicadores = [k for k in indicadores if k["id_proceso"] in criticos]

    cabeceras = {
        "apikey": config.SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    ajustados = 0
    sin_correspondencia = []

    for kpi in indicadores:
        nombre = normalizar(kpi["nombre_kpi"])
        ficha = next((f for clave, f in FICHAS.items() if clave in nombre), None)

        if ficha is None:
            sin_correspondencia.append(kpi["nombre_kpi"])
            continue

        print(f"  {kpi['nombre_kpi'][:44]:46}")
        print(f"       queda como: {ficha['nombre_kpi']}")
        print(
            f"       meta {ficha['meta']} {ficha['unidad_medida']} · "
            f"{'ascendente' if ficha['tipo_medicion'] == ASCENDENTE else 'descendente'}"
        )

        if not simular:
            respuesta = requests.patch(
                f"{config.SUPABASE_URL}/rest/v1/indicador_kpi",
                headers=cabeceras,
                params={"id_kpi": f"eq.{kpi['id_kpi']}"},
                json={**ficha, "estado": "Implementado", "viable": "Si"},
                timeout=45,
            )
            if respuesta.status_code >= 400:
                print(f"       error: {respuesta.status_code}")
                continue

        ajustados += 1

    print()
    print(f"  Indicadores alineados: {ajustados} de {len(indicadores)}")

    if sin_correspondencia:
        print()
        print("  Sin correspondencia en las fichas técnicas:")
        for nombre in sin_correspondencia:
            print(f"    {nombre}")

    if simular:
        print()
        print("  Modo simulación: no se escribió nada en la base de datos.")


if __name__ == "__main__":
    main()
