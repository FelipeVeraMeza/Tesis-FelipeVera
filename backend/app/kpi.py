"""
Logica de negocio de los indicadores.

Consolida las lecturas de la base de datos, evalua el cumplimiento respecto a
la meta y calcula la proyeccion de tendencia (regresion lineal simple) exigida
por el RF10, dentro del limite declarado en el alcance: proyecciones
estadisticas lineales, sin algoritmos de Machine Learning.
"""
from . import db

# Umbral bajo el cual un KPI se considera "en riesgo" en lugar de "bajo desempeno"
UMBRAL_RIESGO = 0.80

NOMBRES_GRAFICO = {1: "bar", 2: "line", 3: "pie"}


def evaluar_estado(valor: float | None, meta: float | None, tipo_medicion: int) -> str:
    """
    Clasifica el desempeno de un KPI segun su tendencia esperada.

    tipo_medicion 1 = ascendente (mayor es mejor)
    tipo_medicion 2 = descendente (menor es mejor)
    """
    if valor is None or meta is None:
        return "sin_datos"

    if tipo_medicion == 2:
        if valor <= meta:
            return "cumple"
        # Para metas descendentes el margen de riesgo se mide hacia arriba
        return "riesgo" if meta and valor <= meta * (2 - UMBRAL_RIESGO) else "bajo"

    if valor >= meta:
        return "cumple"
    return "riesgo" if meta and valor >= meta * UMBRAL_RIESGO else "bajo"


def porcentaje_cumplimiento(valor: float | None, meta: float | None, tipo_medicion: int) -> float | None:
    """
    Porcentaje de cumplimiento acotado a 100 %, usado en las tarjetas resumen.

    Devuelve None cuando no hay elementos suficientes para calcularlo, de modo
    que el indicador quede excluido del promedio en lugar de contarse como cero.
    """
    if valor is None or meta is None:
        return None

    # Con meta cero, el cumplimiento se evalua por el estado y no por razon
    if meta == 0:
        return 100.0 if evaluar_estado(valor, meta, tipo_medicion) == "cumple" else 0.0

    if tipo_medicion == 2:
        # Metas descendentes: alcanzar o bajar de la meta es cumplimiento pleno
        if valor <= meta:
            return 100.0
        if valor <= 0:
            return 100.0
        razon = meta / valor
    else:
        if valor >= meta:
            return 100.0
        # Metas negativas (p. ej. desviaciones) no admiten una razon directa
        if meta <= 0:
            return None
        razon = valor / meta

    return round(max(min(razon, 1.0), 0.0) * 100, 1)


def analizar_tendencia(
    valores: list[float],
    limite_inferior: float | None = None,
    limite_superior: float | None = None,
) -> dict | None:
    """
    Analisis estadistico de la serie historica de un indicador (RF10).

    Ajusta una recta por minimos cuadrados y devuelve, ademas de la
    proyeccion, indicadores que permiten interpretar su confiabilidad:

      pendiente      variacion promedio por periodo
      r2             bondad del ajuste (0 a 1)
      confiabilidad  lectura cualitativa del r2
      direccion      sentido de la tendencia observada
      volatilidad    desviacion estandar de la serie

    Conforme al alcance declarado, el analisis se mantiene dentro de las
    tecnicas estadisticas lineales, sin recurrir a algoritmos de aprendizaje
    automatico.
    """
    n = len(valores)
    if n < 3:
        return None

    xs = list(range(n))
    media_x = sum(xs) / n
    media_y = sum(valores) / n

    varianza_x = sum((x - media_x) ** 2 for x in xs)
    if varianza_x == 0:
        return None

    pendiente = sum((x - media_x) * (y - media_y) for x, y in zip(xs, valores)) / varianza_x
    intercepto = media_y - pendiente * media_x

    # Coeficiente de determinacion: proporcion de la variacion explicada
    suma_total = sum((y - media_y) ** 2 for y in valores)
    suma_residual = sum((y - (pendiente * x + intercepto)) ** 2 for x, y in zip(xs, valores))
    r2 = 1 - (suma_residual / suma_total) if suma_total > 0 else 1.0

    proyeccion = pendiente * n + intercepto
    if limite_inferior is not None:
        proyeccion = max(proyeccion, limite_inferior)
    if limite_superior is not None:
        proyeccion = min(proyeccion, limite_superior)

    varianza = sum((y - media_y) ** 2 for y in valores) / n

    if r2 >= 0.7:
        confiabilidad = "alta"
    elif r2 >= 0.4:
        confiabilidad = "media"
    else:
        confiabilidad = "baja"

    # Se considera estable cuando la variacion por periodo es marginal
    umbral = abs(media_y) * 0.01 if media_y else 0.01
    if abs(pendiente) < umbral:
        direccion = "estable"
    else:
        direccion = "ascendente" if pendiente > 0 else "descendente"

    return {
        "proyeccion": round(proyeccion, 2),
        "pendiente": round(pendiente, 3),
        "r2": round(max(r2, 0.0), 3),
        "confiabilidad": confiabilidad,
        "direccion": direccion,
        "volatilidad": round(varianza**0.5, 2),
        "periodos": n,
    }


def proyectar(
    valores: list[float],
    periodos_futuros: int = 1,
    limite_inferior: float | None = None,
    limite_superior: float | None = None,
) -> float | None:
    """
    Proyeccion lineal por minimos cuadrados sobre la serie historica (RF10).

    El resultado se acota al rango valido del indicador, para no proyectar
    valores imposibles (por ejemplo, un porcentaje negativo).

    Devuelve None si no hay suficientes puntos para trazar una tendencia.
    """
    n = len(valores)
    if n < 3:
        return None

    xs = list(range(n))
    media_x = sum(xs) / n
    media_y = sum(valores) / n

    denominador = sum((x - media_x) ** 2 for x in xs)
    if denominador == 0:
        return None

    pendiente = sum((x - media_x) * (y - media_y) for x, y in zip(xs, valores)) / denominador
    intercepto = media_y - pendiente * media_x
    proyeccion = pendiente * (n - 1 + periodos_futuros) + intercepto

    if limite_inferior is not None:
        proyeccion = max(proyeccion, limite_inferior)
    if limite_superior is not None:
        proyeccion = min(proyeccion, limite_superior)

    return round(proyeccion, 2)


def _serie_historica(resultados: list[dict], id_kpi: int) -> list[dict]:
    serie = [r for r in resultados if r["id_kpi"] == id_kpi]
    return sorted(serie, key=lambda r: r["periodo"])


def obtener_kpis(codigo_proceso: str | None = None) -> list[dict]:
    """
    Devuelve los KPI con su ultimo resultado, estado de cumplimiento,
    serie historica y proyeccion. Si se indica `codigo_proceso`, filtra
    solo los indicadores de ese proceso.
    """
    procesos = db.seleccionar(
        "proceso_ti",
        {"select": "id_proceso,nombre_proceso,codigo_proceso,responsable,estado,critico"},
    )
    mapa_procesos = {p["id_proceso"]: p for p in procesos}

    if codigo_proceso == "criticos":
        # Conjunto de los cuatro procesos definidos en el alcance
        ids_validos = {p["id_proceso"] for p in procesos if p.get("critico")}
    elif codigo_proceso and codigo_proceso != "general":
        ids_validos = {
            p["id_proceso"] for p in procesos if p["codigo_proceso"] == codigo_proceso
        }
        if not ids_validos:
            return []
    else:
        ids_validos = set(mapa_procesos)

    indicadores = db.seleccionar("indicador_kpi", {"select": "*", "order": "id_kpi"})
    indicadores = [k for k in indicadores if k["id_proceso"] in ids_validos]

    resultados = db.seleccionar(
        "resultado_kpi",
        {"select": "id_kpi,valor_real,fecha_registro,periodo", "order": "periodo"},
    )

    salida = []
    for kpi in indicadores:
        serie = _serie_historica(resultados, kpi["id_kpi"])
        valores = [float(r["valor_real"]) for r in serie]

        valor_actual = valores[-1] if valores else None
        meta = float(kpi["meta"]) if kpi["meta"] is not None else None
        tipo_medicion = int(kpi.get("tipo_medicion") or 1)

        proceso = mapa_procesos.get(kpi["id_proceso"], {})

        limite_inf = (
            float(kpi["valor_minimo"]) if kpi.get("valor_minimo") is not None else None
        )
        limite_sup = (
            float(kpi["valor_maximo"]) if kpi.get("valor_maximo") is not None else None
        )
        tendencia_serie = analizar_tendencia(valores, limite_inf, limite_sup)

        salida.append(
            {
                "id_kpi": kpi["id_kpi"],
                "codigo_kpi": kpi["codigo_kpi"],
                "nombre": kpi["nombre_kpi"],
                "descripcion": kpi["descripcion"],
                "formula": kpi["formula"],
                "unidad": kpi["unidad_medida"],
                "periodicidad": kpi["periodicidad"],
                "meta": meta,
                "valor": valor_actual,
                "tipo_medicion": tipo_medicion,
                "tendencia": "descendente" if tipo_medicion == 2 else "ascendente",
                "tipo_grafico": NOMBRES_GRAFICO.get(int(kpi.get("tipo_grafico") or 1), "bar"),
                "estado": evaluar_estado(valor_actual, meta, tipo_medicion),
                "cumplimiento": porcentaje_cumplimiento(valor_actual, meta, tipo_medicion),
                "proyeccion": tendencia_serie["proyeccion"] if tendencia_serie else None,
                "analisis": tendencia_serie,
                "proceso": proceso.get("codigo_proceso"),
                "proceso_nombre": proceso.get("nombre_proceso"),
                "proceso_critico": bool(proceso.get("critico")),
                "dueno_proceso": kpi.get("dueno_proceso"),
                "viable": kpi.get("viable"),
                "estado_implementacion": kpi.get("estado"),
                "perspectiva": kpi.get("perspectiva"),
                "fuente_origen": kpi.get("fuente_origen"),
                "historico": [
                    {"periodo": r["periodo"], "valor": float(r["valor_real"])}
                    for r in serie
                ],
            }
        )

    return salida


def resumen_por_proceso() -> list[dict]:
    """
    Cumplimiento promedio por proceso, para las tarjetas del panel ejecutivo.

    El promedio considera unicamente los indicadores que cuentan con medicion;
    los que aun no se implementan se informan aparte, para no distorsionar el
    resultado del proceso.
    """
    kpis = obtener_kpis()
    agrupado: dict[str, dict] = {}

    for kpi in kpis:
        codigo = kpi["proceso"]
        if not codigo:
            continue
        bloque = agrupado.setdefault(
            codigo,
            {
                "proceso": codigo,
                "nombre": kpi["proceso_nombre"],
                "critico": kpi["proceso_critico"],
                "cumplimientos": [],
                "total_kpis": 0,
                "kpis_medidos": 0,
                "en_alerta": 0,
            },
        )
        bloque["total_kpis"] += 1

        if kpi["estado"] == "sin_datos":
            continue

        bloque["kpis_medidos"] += 1
        if kpi["cumplimiento"] is not None:
            bloque["cumplimientos"].append(kpi["cumplimiento"])
        if kpi["estado"] in ("riesgo", "bajo"):
            bloque["en_alerta"] += 1

    resumen = []
    for bloque in agrupado.values():
        valores = bloque.pop("cumplimientos")
        bloque["cumplimiento_promedio"] = (
            round(sum(valores) / len(valores), 1) if valores else None
        )
        resumen.append(bloque)

    # Los procesos criticos encabezan el panel
    return sorted(resumen, key=lambda b: (not b["critico"], b["nombre"]))


def alertas(solo_criticos: bool = False) -> list[dict]:
    """
    KPI fuera de meta, que alimentan el panel de alertas automaticas (RF7).

    Con `solo_criticos` la lista se acota a los cuatro procesos definidos en el
    alcance del proyecto.
    """
    encontradas = [
        {
            "id_kpi": k["id_kpi"],
            "kpi": k["nombre"],
            "proceso": k["proceso_nombre"],
            "valor": k["valor"],
            "meta": k["meta"],
            "unidad": k["unidad"],
            "estado": k["estado"],
            "critico": k["proceso_critico"],
            "dueno_proceso": k["dueno_proceso"],
        }
        for k in obtener_kpis()
        if k["estado"] in ("riesgo", "bajo")
    ]

    if solo_criticos:
        encontradas = [a for a in encontradas if a["critico"]]

    # Las desviaciones mas severas encabezan la lista
    return sorted(encontradas, key=lambda a: (a["estado"] != "bajo", not a["critico"]))


def periodos_disponibles() -> list[str]:
    """Períodos con mediciones registradas, del más reciente al más antiguo."""
    filas = db.seleccionar("resultado_kpi", {"select": "periodo"})
    return sorted({f["periodo"] for f in filas}, reverse=True)


def estado_general(codigo_proceso: str | None = None) -> dict:
    """
    Síntesis del desempeño para el encabezado del panel.

    Consolida el cumplimiento global, la cobertura de medición y la variación
    respecto al período anterior, de modo que la situación se lea de un vistazo
    sin recorrer el detalle.
    """
    indicadores = obtener_kpis(codigo_proceso)
    procesos = resumen_por_proceso()

    if codigo_proceso == "criticos":
        procesos = [p for p in procesos if p["critico"]]
    elif codigo_proceso and codigo_proceso != "general":
        procesos = [p for p in procesos if p["proceso"] == codigo_proceso]

    medidos = [k for k in indicadores if k["estado"] != "sin_datos"]
    cumplen = [k for k in medidos if k["estado"] == "cumple"]
    desviados = [k for k in medidos if k["estado"] in ("riesgo", "bajo")]
    criticos = [k for k in medidos if k["estado"] == "bajo"]

    cumplimientos = [k["cumplimiento"] for k in medidos if k["cumplimiento"] is not None]
    global_actual = round(sum(cumplimientos) / len(cumplimientos), 1) if cumplimientos else None

    # Variación respecto al período anterior, calculada sobre los indicadores
    # que disponen de al menos dos mediciones
    variacion = _variacion_periodo(medidos)

    procesos_en_meta = [
        p for p in procesos
        if p["cumplimiento_promedio"] is not None and p["cumplimiento_promedio"] >= 90
    ]

    periodos = periodos_disponibles()

    return {
        "cumplimiento_global": global_actual,
        "variacion": variacion,
        "indicadores_totales": len(indicadores),
        "indicadores_medidos": len(medidos),
        "indicadores_cumplen": len(cumplen),
        "indicadores_desviados": len(desviados),
        "indicadores_criticos": len(criticos),
        "procesos_totales": len(procesos),
        "procesos_en_meta": len(procesos_en_meta),
        "periodo_actual": periodos[0] if periodos else None,
        "periodos": periodos,
    }


def _variacion_periodo(indicadores: list[dict]) -> float | None:
    """
    Diferencia en puntos porcentuales entre el cumplimiento del último período
    y el anterior. Devuelve None si no hay serie suficiente para compararlos.
    """
    actuales, previos = [], []

    for kpi in indicadores:
        serie = kpi["historico"]
        if len(serie) < 2 or kpi["meta"] is None:
            continue

        for valores, punto in ((actuales, serie[-1]), (previos, serie[-2])):
            cumplimiento = porcentaje_cumplimiento(
                punto["valor"], kpi["meta"], kpi["tipo_medicion"]
            )
            if cumplimiento is not None:
                valores.append(cumplimiento)

    if not actuales or not previos:
        return None

    return round(sum(actuales) / len(actuales) - sum(previos) / len(previos), 1)


def evolucion_cumplimiento(codigo_proceso: str | None = None) -> list[dict]:
    """
    Cumplimiento promedio por período, para el gráfico de evolución.

    Permite observar si el desempeño del conjunto mejora o se deteriora, más
    allá del resultado de cada indicador por separado.
    """
    indicadores = obtener_kpis(codigo_proceso)

    por_periodo: dict[str, list[float]] = {}
    for kpi in indicadores:
        if kpi["meta"] is None:
            continue
        for punto in kpi["historico"]:
            cumplimiento = porcentaje_cumplimiento(
                punto["valor"], kpi["meta"], kpi["tipo_medicion"]
            )
            if cumplimiento is not None:
                por_periodo.setdefault(punto["periodo"], []).append(cumplimiento)

    return [
        {
            "periodo": periodo,
            "cumplimiento": round(sum(valores) / len(valores), 1),
            "indicadores": len(valores),
        }
        for periodo, valores in sorted(por_periodo.items())
    ]
