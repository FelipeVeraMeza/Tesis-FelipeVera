"""
Proceso ETL: extraccion, transformacion y carga.

Lee los archivos CSV entregados por los responsables de proceso, valida su
formato e integridad (RF2), aplica las formulas de calculo definidas en las
fichas tecnicas de KPI (RF3) y registra los resultados en la base de datos.

Cada proceso critico tiene su propio formato de archivo. Los formatos
esperados estan documentados en backend/data_ejemplo/.
"""
import csv
import io
import re
import unicodedata

from . import db

PATRON_PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Palabras que identifican a cada indicador dentro del catalogo.
#
# El catalogo puede provenir de la carga inicial o de la importacion de la
# planilla institucional, y los codigos difieren entre ambas fuentes. Por eso
# la correspondencia se resuelve por el nombre del indicador y no por un
# codigo fijo.
SENALES_KPI = {
    "cam_tasa_aceptacion": ("tasa", "aceptacion", "cambio"),
    "cam_urgentes": ("cambio", "urgente"),
    "cam_vuelta_atras": ("cambio", "vuelta atras"),
    "cam_error_certificacion": ("cambio", "certificacion"),
    "inc_tiempo_resolucion": ("tiempo", "resolucion", "incidente"),
    "inc_capacidad_cierre": ("capacidad", "cierre", "incidente"),
    "req_rechazados": ("requerimiento", "rechazad"),
    "req_tiempo_medio": ("tiempo", "resolucion", "requerimiento"),
    "req_sla": ("requerimiento", "sla"),
    "dem_tiempo_ciclo": ("tiempo", "demanda"),
    "dem_sla_evaluacion": ("solicitud", "demanda", "evaluad"),
}


def _normalizar(texto: str) -> str:
    limpio = unicodedata.normalize("NFKD", str(texto or "").lower())
    return "".join(c for c in limpio if not unicodedata.combining(c))


def convertir_excel(contenido: bytes) -> str:
    """
    Convierte una planilla de calculo a texto CSV (RF1).

    Se lee la primera hoja del libro y se traduce a CSV, de modo que el resto
    del proceso ETL opera sin distinguir el formato de origen.
    """
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise ErrorETL(
            "La lectura de archivos Excel requiere la biblioteca openpyxl. "
            "Ejecute: pip install openpyxl"
        ) from exc

    try:
        libro = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True, read_only=True)
    except Exception as exc:  # noqa: BLE001
        raise ErrorETL(f"No se pudo leer el archivo Excel: {exc}") from exc

    hoja = libro.worksheets[0]

    salida = io.StringIO()
    escritor = csv.writer(salida)
    filas_escritas = 0

    for fila in hoja.iter_rows(values_only=True):
        # Se omiten las filas completamente vacias que suelen quedar al final
        if all(celda is None or str(celda).strip() == "" for celda in fila):
            continue
        escritor.writerow(
            ["" if celda is None else str(celda).strip() for celda in fila]
        )
        filas_escritas += 1

    libro.close()

    if filas_escritas < 2:
        raise ErrorETL("La planilla no contiene datos bajo la fila de encabezados.")

    return salida.getvalue()


def mapear_catalogo() -> dict[str, int]:
    """
    Relaciona cada indicador calculado por el ETL con su registro en la base.

    Primero busca una coincidencia exacta de codigo; si no la encuentra,
    identifica el indicador por las palabras clave de su nombre.
    """
    catalogo = db.seleccionar("indicador_kpi", {"select": "id_kpi,codigo_kpi,nombre_kpi"})
    por_codigo = {k["codigo_kpi"]: k["id_kpi"] for k in catalogo}

    mapa: dict[str, int] = {}
    for codigo, senales in SENALES_KPI.items():
        if codigo in por_codigo:
            mapa[codigo] = por_codigo[codigo]
            continue

        for registro in catalogo:
            nombre = _normalizar(registro["nombre_kpi"])
            if all(s in nombre for s in senales):
                mapa[codigo] = registro["id_kpi"]
                break

    return mapa


class ErrorETL(Exception):
    """Error de validacion o de calculo durante la carga."""


# ------------------------------------------------------------------
# Definicion de los archivos esperados por proceso
# ------------------------------------------------------------------
COLUMNAS_ESPERADAS = {
    "cambios": [
        "periodo",
        "cambios_solicitados",
        "cambios_aceptados",
        "cambios_urgentes",
        "cambios_implementados",
        "cambios_revertidos",
        "cambios_error_certificacion",
    ],
    "incidentes": [
        "periodo",
        "incidentes_creados",
        "incidentes_cerrados",
        "horas_totales_resolucion",
    ],
    "requerimientos": [
        "periodo",
        "requerimientos_cerrados",
        "requerimientos_rechazados",
        "dias_totales_resolucion",
        "requerimientos_dentro_sla",
    ],
    "demanda": [
        "periodo",
        "solicitudes_totales",
        "dias_totales_evaluacion",
        "solicitudes_dentro_sla",
    ],
}


def _division(numerador: float, denominador: float) -> float | None:
    """Division protegida: devuelve None si el denominador es cero."""
    if not denominador:
        return None
    return numerador / denominador


# ------------------------------------------------------------------
# Limpieza y normalizacion (pandas / NumPy)
# ------------------------------------------------------------------
def normalizar_datos(filas: list[dict], proceso: str) -> tuple[list[dict], list[str]]:
    """
    Limpieza y normalizacion de la serie mediante pandas y NumPy.

    Sobre las filas ya validadas se aplican dos tratamientos:

    - Ordenamiento cronologico, para que la serie historica quede
      consistente con independencia del orden del archivo.
    - Deteccion de valores atipicos por desviacion respecto a la media,
      que se informan como advertencia sin descartar el dato, dado que
      pueden corresponder a situaciones operativas reales.

    Si las bibliotecas no estan disponibles, el proceso continua con las
    filas en su orden original.
    """
    if not filas:
        return filas, []

    try:
        import numpy as np
        import pandas as pd
    except ImportError:  # pragma: no cover
        return filas, []

    marco = pd.DataFrame(filas).sort_values("periodo").reset_index(drop=True)
    advertencias: list[str] = []

    # La deteccion se basa en la desviacion absoluta respecto a la mediana
    # (MAD) y no en la desviacion estandar, porque esta ultima se ve
    # distorsionada por el propio valor atipico cuando la serie es corta.
    UMBRAL = 3.5
    FACTOR = 0.6745  # convierte la MAD en una escala comparable a sigma

    for columna in COLUMNAS_ESPERADAS[proceso][1:]:
        serie = pd.to_numeric(marco[columna], errors="coerce")
        if serie.count() < 4:
            continue

        mediana = serie.median()
        mad = np.median(np.abs(serie - mediana))

        if not mad or np.isnan(mad):
            continue

        distancia = FACTOR * np.abs(serie - mediana) / mad
        for posicion in marco.index[distancia > UMBRAL]:
            advertencias.append(
                f"Periodo {marco.at[posicion, 'periodo']}: "
                f"'{columna}' presenta un valor atipico ({serie[posicion]:g}) "
                f"frente al valor habitual de la serie ({mediana:g}). "
                f"Se registra igualmente."
            )

    return marco.to_dict("records"), advertencias


# ------------------------------------------------------------------
# Formulas de calculo (Tablas 11 a 14 de la memoria)
# ------------------------------------------------------------------
def _kpis_cambios(f: dict) -> dict:
    return {
        "cam_tasa_aceptacion": _pct(
            _division(f["cambios_aceptados"], f["cambios_solicitados"])
        ),
        "cam_urgentes": _pct(
            _division(f["cambios_urgentes"], f["cambios_solicitados"])
        ),
        "cam_vuelta_atras": _pct(
            _division(f["cambios_revertidos"], f["cambios_implementados"])
        ),
        "cam_error_certificacion": _pct(
            _division(f["cambios_error_certificacion"], f["cambios_implementados"])
        ),
    }


def _kpis_incidentes(f: dict) -> dict:
    tiempo = _division(f["horas_totales_resolucion"], f["incidentes_cerrados"])
    return {
        "inc_tiempo_resolucion": round(tiempo, 2) if tiempo is not None else None,
        "inc_capacidad_cierre": _pct(
            _division(f["incidentes_cerrados"], f["incidentes_creados"])
        ),
    }


def _kpis_requerimientos(f: dict) -> dict:
    tiempo = _division(f["dias_totales_resolucion"], f["requerimientos_cerrados"])
    return {
        "req_rechazados": f["requerimientos_rechazados"],
        "req_tiempo_medio": round(tiempo, 2) if tiempo is not None else None,
        "req_sla": _pct(
            _division(f["requerimientos_dentro_sla"], f["requerimientos_cerrados"])
        ),
    }


def _kpis_demanda(f: dict) -> dict:
    tiempo = _division(f["dias_totales_evaluacion"], f["solicitudes_totales"])
    return {
        "dem_tiempo_ciclo": round(tiempo, 2) if tiempo is not None else None,
        "dem_sla_evaluacion": _pct(
            _division(f["solicitudes_dentro_sla"], f["solicitudes_totales"])
        ),
    }


def _pct(razon: float | None) -> float | None:
    return round(razon * 100, 2) if razon is not None else None


CALCULADORAS = {
    "cambios": _kpis_cambios,
    "incidentes": _kpis_incidentes,
    "requerimientos": _kpis_requerimientos,
    "demanda": _kpis_demanda,
}


# ------------------------------------------------------------------
# Extraccion y validacion (RF1 y RF2)
# ------------------------------------------------------------------
def validar_y_leer(contenido: str, proceso: str) -> tuple[list[dict], list[str]]:
    """
    Valida la estructura del CSV y convierte sus filas a valores numericos.

    Devuelve las filas validas y la lista de advertencias encontradas. Lanza
    ErrorETL solo cuando el archivo es inutilizable.
    """
    if proceso not in COLUMNAS_ESPERADAS:
        raise ErrorETL(f"Proceso no reconocido: {proceso}")

    esperadas = COLUMNAS_ESPERADAS[proceso]
    lector = csv.DictReader(io.StringIO(contenido.lstrip("﻿")))

    if lector.fieldnames is None:
        raise ErrorETL("El archivo esta vacio o no tiene encabezados.")

    encabezados = [c.strip().lower() for c in lector.fieldnames]
    faltantes = [c for c in esperadas if c not in encabezados]
    if faltantes:
        raise ErrorETL(
            "Faltan columnas obligatorias en el archivo: " + ", ".join(faltantes)
        )

    filas_validas: list[dict] = []
    advertencias: list[str] = []
    periodos_vistos: set[str] = set()

    for numero, fila_cruda in enumerate(lector, start=2):
        fila = {
            (k.strip().lower() if k else ""): (v.strip() if v else "")
            for k, v in fila_cruda.items()
        }

        periodo = fila.get("periodo", "")
        if not PATRON_PERIODO.match(periodo):
            advertencias.append(
                f"Fila {numero}: periodo '{periodo}' invalido, se esperaba AAAA-MM. Fila omitida."
            )
            continue

        if periodo in periodos_vistos:
            advertencias.append(
                f"Fila {numero}: periodo {periodo} duplicado en el archivo. Fila omitida."
            )
            continue

        registro: dict = {"periodo": periodo}
        error_numerico = False

        for columna in esperadas[1:]:
            valor = fila.get(columna, "")
            try:
                numero_valor = float(valor.replace(",", "."))
            except ValueError:
                advertencias.append(
                    f"Fila {numero}: '{columna}' no es numerico ('{valor}'). Fila omitida."
                )
                error_numerico = True
                break
            if numero_valor < 0:
                advertencias.append(
                    f"Fila {numero}: '{columna}' es negativo. Fila omitida."
                )
                error_numerico = True
                break
            registro[columna] = numero_valor

        if error_numerico:
            continue

        # Coherencia entre totales y subconjuntos
        for parte, total in _reglas_coherencia(proceso):
            if registro.get(parte, 0) > registro.get(total, 0):
                advertencias.append(
                    f"Fila {numero}: '{parte}' supera a '{total}' en el periodo {periodo}."
                )

        periodos_vistos.add(periodo)
        filas_validas.append(registro)

    if not filas_validas:
        raise ErrorETL(
            "Ninguna fila del archivo supero la validacion. " + " ".join(advertencias[:5])
        )

    return filas_validas, advertencias


def _reglas_coherencia(proceso: str) -> list[tuple[str, str]]:
    return {
        "cambios": [
            ("cambios_aceptados", "cambios_solicitados"),
            ("cambios_urgentes", "cambios_solicitados"),
            ("cambios_revertidos", "cambios_implementados"),
            ("cambios_error_certificacion", "cambios_implementados"),
        ],
        "incidentes": [("incidentes_cerrados", "incidentes_creados")],
        "requerimientos": [
            ("requerimientos_dentro_sla", "requerimientos_cerrados"),
        ],
        "demanda": [("solicitudes_dentro_sla", "solicitudes_totales")],
    }.get(proceso, [])


# ------------------------------------------------------------------
# Transformacion y carga (RF3)
# ------------------------------------------------------------------
def procesar_archivo(
    contenido: str,
    proceso: str,
    nombre_archivo: str,
    usuario: dict | None = None,
    tipo_fuente: str = "CSV",
) -> dict:
    """
    Ejecuta el ciclo ETL completo para un archivo y devuelve un resumen de la carga.

    Cada carga queda registrada con el usuario responsable, la fecha y la
    procedencia del archivo, de modo que exista trazabilidad completa de las
    actualizaciones realizadas sobre la informacion.
    """
    filas, advertencias = validar_y_leer(contenido, proceso)

    # Limpieza y normalizacion de la serie antes del calculo
    filas, avisos_normalizacion = normalizar_datos(filas, proceso)
    advertencias.extend(avisos_normalizacion)

    mapa_kpi = mapear_catalogo()
    if not mapa_kpi:
        raise ErrorETL(
            "No se encontraron los indicadores en el catalogo. "
            "Ejecute la inicializacion o la importacion del catalogo."
        )

    periodos = sorted({f["periodo"] for f in filas})
    responsable = (usuario or {}).get("nombre", "Sistema")

    fuente = db.insertar(
        "fuente_dato",
        {
            "nombre_fuente": nombre_archivo[:100],
            "tipo_fuente": tipo_fuente,
            "descripcion": f"Carga del proceso {proceso} realizada por {responsable}"[:200],
            "id_usuario": (usuario or {}).get("id_usuario"),
            "proceso": proceso,
            "filas_procesadas": len(filas),
            "periodos_cargados": ", ".join(periodos)[:200],
            "advertencias": len(advertencias),
        },
    )
    id_fuente = fuente[0]["id_fuente"] if fuente else None

    calcular = CALCULADORAS[proceso]
    registros: list[dict] = []

    for fila in filas:
        for codigo, valor in calcular(fila).items():
            if valor is None:
                advertencias.append(
                    f"Periodo {fila['periodo']}: '{codigo}' no se pudo calcular (division por cero)."
                )
                continue
            if codigo not in mapa_kpi:
                advertencias.append(
                    f"El indicador '{codigo}' no esta registrado en el catalogo actual."
                )
                continue
            registros.append(
                {
                    "id_kpi": mapa_kpi[codigo],
                    "valor_real": valor,
                    "periodo": fila["periodo"],
                    "fecha_registro": f"{fila['periodo']}-01",
                    "id_fuente": id_fuente,
                }
            )

    if not registros:
        raise ErrorETL("No se genero ningun resultado calculable a partir del archivo.")

    # Recargar un periodo actualiza el resultado en lugar de duplicarlo
    db.upsert("resultado_kpi", registros, on_conflict="id_kpi,periodo")

    return {
        "proceso": proceso,
        "archivo": nombre_archivo,
        "tipo_fuente": tipo_fuente,
        "periodos_procesados": periodos,
        "filas_leidas": len(filas),
        "resultados_registrados": len(registros),
        "advertencias": advertencias,
        "id_fuente": id_fuente,
        "responsable": responsable,
    }
