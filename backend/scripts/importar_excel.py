"""
Importación del catálogo de KPIs desde el Excel institucional.

Lee la hoja "KPIs" del archivo KPIs_TI_Procesos_v2.xlsx —el levantamiento
realizado en la Gerencia de TI— y carga en la base de datos los procesos, las
fichas técnicas de cada indicador y la serie histórica de valores medidos entre
septiembre de 2024 y marzo de 2025.

Uso:
    python backend/importar_excel.py "<ruta al archivo .xlsx>"
    python backend/importar_excel.py "<ruta>" --simular   (no escribe en la base)
"""
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from app import db  # noqa: E402

# Meses de la hoja de cálculo y el período al que corresponden
COLUMNAS_MES = {
    "Valor efectivo septiembre": "2024-09",
    "Valor efectivo octubre": "2024-10",
    "Valor efectivo noviembre": "2024-11",
    "Valor efectivo diciembre": "2024-12",
    "Valor efectivo Enero 25": "2025-01",
    "Valor efectivo Febrero 25": "2025-02",
    "Valor efectivo Marzo 25": "2025-03",
}

# Los cuatro procesos definidos como críticos en el alcance del proyecto
PROCESOS_CRITICOS = {
    "gestion de cambios ti": "cambios",
    "gestion de incidentes ti": "incidentes",
    "gestion de requerimientos ti": "requerimientos",
    "gestion de la demanda ti": "demanda",
}


def normalizar(texto: str) -> str:
    """Minúsculas sin acentos, para comparar nombres de forma tolerante."""
    limpio = unicodedata.normalize("NFKD", str(texto or "").strip())
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", limpio).lower()


def codigo_desde(texto: str, largo: int = 45) -> str:
    """Genera un identificador estable a partir de un nombre."""
    base = re.sub(r"[^a-z0-9]+", "_", normalizar(texto)).strip("_")
    return base[:largo] or "sin_nombre"


def limpiar(valor):
    """Convierte los vacíos de pandas en None."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


def texto(valor, largo: int) -> str | None:
    """Normaliza un texto y lo recorta al largo que admite la columna."""
    valor = limpiar(valor)
    if valor is None:
        return None
    return re.sub(r"\s+", " ", str(valor).strip())[:largo]


def numero(valor) -> float | None:
    valor = limpiar(valor)
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def es_porcentual(fila: dict) -> bool:
    """
    Determina si el indicador se expresa como proporción.

    En la planilla los KPI porcentuales se registran como fracción (0 a 1);
    aquí se convierten a porcentaje para que coincidan con las fichas técnicas
    documentadas en la memoria.
    """
    maximo = numero(fila.get("Valor Máximo"))
    meta = numero(fila.get("Meta (Rango)"))

    # La escala se deduce del mayor valor de referencia disponible: si el
    # maximo quedo sin registrar, la meta cumple ese papel.
    referencia = max((v for v in (maximo, meta) if v is not None), default=None)
    if referencia is None or referencia > 1.0001:
        return False

    # Un valor de referencia menor o igual a 1 puede ser una proporcion o un
    # conteo pequeno; el texto del indicador lo aclara.
    texto_kpi = " ".join(
        normalizar(fila.get(campo))
        for campo in ("Formula", "Nombre del KPI", "KPI proceso")
    )
    marcas = ("*100", "porcentaje", "tasa", "%", "proporcion", "sla", "/")
    return any(m in texto_kpi for m in marcas)


# Indicadores en los que un valor menor representa un mejor desempeño.
# La columna "Tipo Medición" de la planilla no distingue estos casos de forma
# consistente, por lo que la tendencia se deduce de la naturaleza del
# indicador, según las fichas técnicas documentadas en la memoria.
MARCAS_DESCENDENTE = (
    "tiempo",
    "urgente",
    "vuelta atras",
    "error",
    "falla",
    "incumplimiento",
    "rechaz",
    "desviacion",
    "retraso",
    "reapertura",
    "reproceso",
    "indisponibilidad",
    "caida",
    "brecha",
    "obsolet",
    "vencid",
    "critic",
    "pendiente",
)

MARCAS_ASCENDENTE = (
    "aceptacion",
    "cumplimiento",
    "disponibilidad",
    "cobertura",
    "satisfaccion",
    "actualizacion",
    "exito",
    "capacidad de cierre",
    "dentro de sla",
    "resueltos dentro",
)


def tendencia_de(fila: dict) -> int:
    """
    Determina si el indicador es ascendente (1) o descendente (2).

    Se privilegia el significado del indicador por sobre la marca de la
    planilla, porque esta ultima no diferencia ambos casos con consistencia.
    """
    referencia = f"{normalizar(fila.get('Nombre del KPI'))} {normalizar(fila.get('KPI proceso'))}"

    if any(m in referencia for m in MARCAS_ASCENDENTE):
        return 1
    if any(m in referencia for m in MARCAS_DESCENDENTE):
        return 2

    # Sin señales claras, se respeta lo indicado en la planilla
    return 1 if numero(fila.get("Tipo Medición")) == 1 else 2


def unidad_de(fila: dict, porcentual: bool) -> str:
    if porcentual:
        return "%"
    nombre = normalizar(fila.get("Nombre del KPI")) + " " + normalizar(fila.get("Formula"))
    if "tiempo" in nombre or "dias" in nombre or "duracion" in nombre:
        return "días"
    if "cantidad" in nombre or "numero" in nombre or "total" in nombre:
        return "cantidad"
    return "unidad"


def leer_excel(ruta: Path) -> pd.DataFrame:
    df = pd.read_excel(ruta, sheet_name="KPIs")
    df.columns = [str(c).strip() for c in df.columns]
    # Se descartan las filas sin nombre de indicador
    return df[df["Nombre del KPI"].notna()].copy()


def construir_registros(df: pd.DataFrame) -> tuple[list, list, list]:
    """Traduce las filas de la planilla al modelo de datos del sistema."""
    procesos: dict[str, dict] = {}
    indicadores: list[dict] = []
    resultados: list[tuple[str, str, float]] = []  # (codigo_kpi, periodo, valor)

    codigos_usados: set[str] = set()

    for _, fila in df.iterrows():
        registro = fila.to_dict()

        nombre_proceso = texto(registro.get("Proceso"), 150) or "Sin proceso asignado"
        clave = normalizar(nombre_proceso)
        codigo_proceso = PROCESOS_CRITICOS.get(clave, codigo_desde(nombre_proceso, 30))

        if codigo_proceso not in procesos:
            procesos[codigo_proceso] = {
                "nombre_proceso": nombre_proceso,
                "codigo_proceso": codigo_proceso,
                "descripcion": texto(registro.get("Perspectiva"), 250),
                "responsable": texto(registro.get("Dueño del proceso"), 100),
                "estado": "Activo",
                "critico": codigo_proceso in PROCESOS_CRITICOS.values(),
            }

        nombre_kpi = texto(registro.get("Nombre del KPI"), 150)
        codigo_kpi = codigo_desde(nombre_kpi)
        # Dos procesos distintos pueden usar el mismo nombre de indicador
        if codigo_kpi in codigos_usados:
            codigo_kpi = f"{codigo_proceso[:12]}_{codigo_kpi}"[:50]
        codigos_usados.add(codigo_kpi)

        porcentual = es_porcentual(registro)
        factor = 100 if porcentual else 1

        minimo = numero(registro.get("Valor Mínimo"))
        maximo = numero(registro.get("Valor Máximo"))
        meta = numero(registro.get("Meta (Rango)"))

        viable = normalizar(registro.get("Viable")) in ("si", "sí")
        estado = texto(registro.get("Estado"), 30) or "No implementado"

        indicadores.append(
            {
                "nombre_kpi": nombre_kpi,
                "codigo_kpi": codigo_kpi,
                "descripcion": texto(registro.get("KPI proceso"), 350),
                "formula": texto(registro.get("Formula"), 350),
                "unidad_medida": unidad_de(registro, porcentual),
                "periodicidad": texto(registro.get("Periodicidad"), 50) or "Mensual",
                "codigo_proceso": codigo_proceso,
                "valor_minimo": round(minimo * factor, 2) if minimo is not None else None,
                "valor_maximo": round(maximo * factor, 2) if maximo is not None else None,
                "meta": round(meta * factor, 2) if meta is not None else None,
                "tipo_medicion": tendencia_de(registro),
                "tipo_grafico": 2 if numero(registro.get("Tipo gráfico")) == 0 else 1,
                "estado": estado,
                "viable": "Si" if viable else "No",
                "dueno_proceso": texto(registro.get("Dueño del proceso"), 100),
                "prioridad_impl": int(numero(registro.get("Prioridad de implementación")) or 0) or None,
                "fuente_origen": texto(registro.get("Fuente  de información"), 50),
                "observaciones": texto(registro.get("Observaciones Internas"), 350),
                "perspectiva": texto(registro.get("Perspectiva"), 100),
            }
        )

        # Los indicadores que la planilla marca como no implementados llevan
        # ceros de relleno en las columnas mensuales. Registrarlos como
        # mediciones daria a entender que el proceso rinde cero, cuando en
        # realidad el indicador aun no se instrumenta.
        if normalizar(registro.get("Estado")) != "implementado":
            continue

        mensuales = {
            periodo: numero(registro.get(columna))
            for columna, periodo in COLUMNAS_MES.items()
        }
        medidos = [v for v in mensuales.values() if v is not None]

        # Una serie compuesta unicamente por ceros no refleja desempeno: son
        # celdas de relleno de un indicador que aun no se instrumenta. En
        # cambio, un cero dentro de una serie con valores reales si es una
        # medicion valida, y a menudo representa una mejora.
        serie_vacia = bool(medidos) and not any(medidos)
        if serie_vacia:
            continue

        for periodo, valor in mensuales.items():
            if valor is None:
                continue
            resultados.append((codigo_kpi, periodo, round(valor * factor, 2)))

    return list(procesos.values()), indicadores, resultados


def cargar(procesos: list, indicadores: list, resultados: list) -> None:
    """Escribe el catálogo en la base de datos, reemplazando el contenido previo."""
    print("  Limpiando el catálogo anterior…")
    for tabla in ("resultado_kpi", "meta_kpi", "indicador_kpi", "proceso_ti"):
        db.eliminar_todo(tabla)

    print(f"  Cargando {len(procesos)} procesos…")
    filas_proceso = db.insertar("proceso_ti", procesos)
    id_proceso = {p["codigo_proceso"]: p["id_proceso"] for p in filas_proceso}

    print(f"  Cargando {len(indicadores)} indicadores…")
    payload = []
    for kpi in indicadores:
        registro = {k: v for k, v in kpi.items() if k not in ("codigo_proceso", "perspectiva")}
        registro["id_proceso"] = id_proceso[kpi["codigo_proceso"]]
        payload.append(registro)

    filas_kpi = db.insertar("indicador_kpi", payload)
    id_kpi = {k["codigo_kpi"]: k["id_kpi"] for k in filas_kpi}

    metas = [
        {
            "id_kpi": k["id_kpi"],
            "valor_objetivo": k["meta"],
            "valor_minimo": k["valor_minimo"],
            "valor_maximo": k["valor_maximo"],
        }
        for k in filas_kpi
        if k.get("meta") is not None
    ]
    if metas:
        print(f"  Cargando {len(metas)} metas…")
        db.insertar("meta_kpi", metas)

    fuente = db.insertar(
        "fuente_dato",
        {
            "nombre_fuente": "KPIs_TI_Procesos_v2.xlsx",
            "tipo_fuente": "Excel",
            "descripcion": "Levantamiento de KPI de la Gerencia de TI",
        },
    )
    id_fuente = fuente[0]["id_fuente"] if fuente else None

    print(f"  Cargando {len(resultados)} resultados históricos…")
    filas = [
        {
            "id_kpi": id_kpi[codigo],
            "valor_real": valor,
            "periodo": periodo,
            "fecha_registro": f"{periodo}-01",
            "id_fuente": id_fuente,
        }
        for codigo, periodo, valor in resultados
        if codigo in id_kpi
    ]
    # Se envía por bloques para no exceder el tamaño de petición
    for inicio in range(0, len(filas), 200):
        db.insertar("resultado_kpi", filas[inicio : inicio + 200])


def resumir(procesos: list, indicadores: list, resultados: list) -> None:
    criticos = [p for p in procesos if p["critico"]]
    viables = [k for k in indicadores if k["viable"] == "Si"]
    implementados = [k for k in indicadores if normalizar(k["estado"]) == "implementado"]
    con_datos = {c for c, _, _ in resultados}

    print()
    print(f"  Procesos            : {len(procesos)}  ({len(criticos)} críticos)")
    print(f"  Indicadores         : {len(indicadores)}")
    print(f"    viables           : {len(viables)}")
    print(f"    implementados     : {len(implementados)}")
    print(f"    con mediciones    : {len(con_datos)}")
    print(f"  Resultados          : {len(resultados)}")
    if resultados:
        periodos = sorted({p for _, p, _ in resultados})
        print(f"  Períodos            : {periodos[0]} a {periodos[-1]}")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ruta = Path(sys.argv[1])
    if not ruta.exists():
        print(f"  No se encontró el archivo: {ruta}")
        sys.exit(1)

    simular = "--simular" in sys.argv

    print("=" * 62)
    print(" Importación del catálogo de KPIs desde Excel")
    print("=" * 62)
    print(f"  Archivo: {ruta.name}")

    df = leer_excel(ruta)
    procesos, indicadores, resultados = construir_registros(df)
    resumir(procesos, indicadores, resultados)

    if simular:
        print()
        print("  Modo simulación: no se escribió nada en la base de datos.")
        return

    print()
    cargar(procesos, indicadores, resultados)
    print()
    print("  Importación completada.")


if __name__ == "__main__":
    main()
