"""
Generación de mediciones simuladas.

El levantamiento realizado en la Gerencia de TI abarca desde septiembre de 2024
hasta marzo de 2025. Para demostrar el comportamiento del sistema sobre una
serie más extensa, este script completa los períodos posteriores con
mediciones simuladas, y cubre los indicadores del alcance que aún no cuentan
con registros.

Las mediciones simuladas se registran bajo una fuente de datos propia,
identificada como «Simulado», de modo que en todo momento sea posible
distinguirlas de las mediciones efectivas provenientes de Jira.

Uso:
    python backend/scripts/generar_periodos.py              # hasta el mes actual
    python backend/scripts/generar_periodos.py --hasta 2026-06
    python backend/scripts/generar_periodos.py --limpiar    # elimina lo simulado
    python backend/scripts/generar_periodos.py --simular    # sin escribir
"""
import random
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db  # noqa: E402

FUENTE_SIMULADA = "Simulado"

# Último período con mediciones efectivas en el levantamiento
ULTIMO_PERIODO_REAL = "2025-03"

# Semilla fija: la serie generada es reproducible entre ejecuciones
SEMILLA = 20250315


def periodos_entre(desde: str, hasta: str) -> list[str]:
    """Períodos mensuales comprendidos entre dos fechas, ambas incluidas."""
    anio, mes = (int(p) for p in desde.split("-"))
    anio_fin, mes_fin = (int(p) for p in hasta.split("-"))

    periodos = []
    while (anio, mes) <= (anio_fin, mes_fin):
        periodos.append(f"{anio:04d}-{mes:02d}")
        mes += 1
        if mes > 12:
            mes = 1
            anio += 1

    return periodos


def periodo_actual() -> str:
    hoy = date.today()
    return f"{hoy.year:04d}-{hoy.month:02d}"


def periodo_siguiente(periodo: str) -> str:
    anio, mes = (int(p) for p in periodo.split("-"))
    mes += 1
    if mes > 12:
        mes = 1
        anio += 1
    return f"{anio:04d}-{mes:02d}"


# ------------------------------------------------------------------
# Generación de la serie
# ------------------------------------------------------------------
def _acotar(valor: float, minimo: float | None, maximo: float | None) -> float:
    if minimo is not None:
        valor = max(valor, minimo)
    if maximo is not None:
        valor = min(valor, maximo)
    return round(valor, 2)


def continuar_serie(
    historico: list[float],
    meta: float | None,
    tipo_medicion: int,
    minimo: float | None,
    maximo: float | None,
    cantidad: int,
    azar: random.Random,
) -> list[float]:
    """
    Extiende una serie histórica conservando su comportamiento.

    La continuación mantiene el nivel y la variabilidad observados, y aplica
    una leve tendencia hacia la meta: los procesos bajo seguimiento tienden a
    corregirse cuando se apartan de su objetivo.
    """
    if not historico:
        return []

    ultimo = historico[-1]

    # Variabilidad observada; con series muy cortas se usa una referencia
    if len(historico) >= 3:
        media = sum(historico) / len(historico)
        dispersion = (sum((v - media) ** 2 for v in historico) / len(historico)) ** 0.5
    else:
        dispersion = abs(ultimo) * 0.06

    dispersion = max(dispersion, abs(ultimo) * 0.02, 0.01)

    serie = []
    valor = ultimo

    for _ in range(cantidad):
        variacion = azar.gauss(0, dispersion * 0.7)

        # Corrección suave hacia la meta cuando el indicador se aparta
        if meta is not None:
            distancia = meta - valor
            fuera_de_meta = (
                (valor < meta) if tipo_medicion == 1 else (valor > meta)
            )
            correccion = distancia * (0.18 if fuera_de_meta else 0.04)
        else:
            correccion = 0

        valor = _acotar(valor + variacion + correccion, minimo, maximo)
        serie.append(valor)

    return serie


def serie_inicial(
    meta: float | None,
    tipo_medicion: int,
    minimo: float | None,
    maximo: float | None,
    cantidad: int,
    azar: random.Random,
) -> list[float]:
    """
    Construye una serie para un indicador sin mediciones previas.

    Parte de un valor próximo a la meta —los procesos del alcance se
    encuentran bajo seguimiento— y evoluciona con variaciones acotadas.
    """
    if meta is None:
        return []

    # Punto de partida algo apartado de la meta, en el sentido desfavorable
    desvio = abs(meta) * azar.uniform(0.05, 0.18)
    valor = meta - desvio if tipo_medicion == 1 else meta + desvio
    valor = _acotar(valor, minimo, maximo)

    return [valor] + continuar_serie(
        [valor], meta, tipo_medicion, minimo, maximo, cantidad - 1, azar
    )


# ------------------------------------------------------------------
# Acceso a los datos
# ------------------------------------------------------------------
def obtener_fuente_simulada() -> int:
    """Identificador de la fuente que agrupa las mediciones simuladas."""
    existentes = db.seleccionar(
        "fuente_dato",
        {"select": "id_fuente,nombre_fuente", "nombre_fuente": f"eq.{FUENTE_SIMULADA}"},
    )
    if existentes:
        return existentes[0]["id_fuente"]

    creada = db.insertar(
        "fuente_dato",
        {
            "nombre_fuente": FUENTE_SIMULADA,
            "tipo_fuente": "Simulado",
            "descripcion": (
                "Mediciones generadas para demostrar el sistema sobre una serie "
                "extendida. No provienen de los registros operativos."
            ),
            "proceso": "todos",
        },
    )
    return creada[0]["id_fuente"]


def limpiar_simulados() -> int:
    """Elimina las mediciones simuladas, conservando las efectivas."""
    fuentes = db.seleccionar(
        "fuente_dato",
        {"select": "id_fuente", "nombre_fuente": f"eq.{FUENTE_SIMULADA}"},
    )
    if not fuentes:
        return 0

    id_fuente = fuentes[0]["id_fuente"]
    resultados = db.seleccionar(
        "resultado_kpi", {"select": "id_resultado", "id_fuente": f"eq.{id_fuente}"}
    )

    import requests

    from app import config

    requests.delete(
        f"{config.SUPABASE_URL}/rest/v1/resultado_kpi",
        headers={
            "apikey": config.SUPABASE_SECRET_KEY,
            "Authorization": f"Bearer {config.SUPABASE_SECRET_KEY}",
        },
        params={"id_fuente": f"eq.{id_fuente}"},
        timeout=60,
    )

    return len(resultados)


# ------------------------------------------------------------------
# Proceso principal
# ------------------------------------------------------------------
def generar(hasta: str, simular: bool = False) -> None:
    azar = random.Random(SEMILLA)

    procesos = db.seleccionar(
        "proceso_ti", {"select": "id_proceso,nombre_proceso,codigo_proceso,critico"}
    )
    criticos = {p["id_proceso"] for p in procesos if p.get("critico")}
    nombres = {p["id_proceso"]: p["nombre_proceso"] for p in procesos}

    indicadores = db.seleccionar("indicador_kpi", {"select": "*", "order": "id_kpi"})
    # El alcance del proyecto comprende los cuatro procesos críticos
    indicadores = [k for k in indicadores if k["id_proceso"] in criticos]

    resultados = db.seleccionar(
        "resultado_kpi", {"select": "id_kpi,valor_real,periodo", "order": "periodo"}
    )

    por_kpi: dict[int, list[dict]] = {}
    for fila in resultados:
        por_kpi.setdefault(fila["id_kpi"], []).append(fila)

    nuevos: list[dict] = []
    resumen: list[str] = []

    for kpi in indicadores:
        serie = sorted(por_kpi.get(kpi["id_kpi"], []), key=lambda r: r["periodo"])
        valores = [float(r["valor_real"]) for r in serie]

        meta = float(kpi["meta"]) if kpi["meta"] is not None else None
        minimo = float(kpi["valor_minimo"]) if kpi["valor_minimo"] is not None else None
        maximo = float(kpi["valor_maximo"]) if kpi["valor_maximo"] is not None else None
        tipo = int(kpi.get("tipo_medicion") or 1)

        if serie:
            desde = periodo_siguiente(serie[-1]["periodo"])
            periodos = periodos_entre(desde, hasta)
            if not periodos:
                resumen.append(f"  {kpi['nombre_kpi'][:44]:46} al día")
                continue
            generados = continuar_serie(valores, meta, tipo, minimo, maximo, len(periodos), azar)
        else:
            # Indicador sin mediciones: se construye la serie completa
            periodos = periodos_entre("2024-09", hasta)
            generados = serie_inicial(meta, tipo, minimo, maximo, len(periodos), azar)
            if not generados:
                resumen.append(f"  {kpi['nombre_kpi'][:44]:46} sin meta definida")
                continue

        for periodo, valor in zip(periodos, generados):
            nuevos.append(
                {
                    "id_kpi": kpi["id_kpi"],
                    "valor_real": valor,
                    "periodo": periodo,
                    "fecha_registro": f"{periodo}-01",
                }
            )

        resumen.append(
            f"  {kpi['nombre_kpi'][:44]:46} "
            f"{nombres.get(kpi['id_proceso'], '')[:20]:22} "
            f"+{len(periodos)} períodos ({periodos[0]} a {periodos[-1]})"
        )

    print("  Indicadores de los procesos críticos:")
    for linea in resumen:
        print(linea)

    print()
    print(f"  Mediciones a generar: {len(nuevos)}")

    if simular:
        print("  Modo simulación: no se escribió nada en la base de datos.")
        return

    if not nuevos:
        print("  No hay períodos pendientes de completar.")
        return

    id_fuente = obtener_fuente_simulada()
    for registro in nuevos:
        registro["id_fuente"] = id_fuente

    for inicio in range(0, len(nuevos), 200):
        db.upsert("resultado_kpi", nuevos[inicio : inicio + 200], on_conflict="id_kpi,periodo")

    print(f"  Registradas bajo la fuente «{FUENTE_SIMULADA}».")


def main() -> None:
    hasta = periodo_actual()
    if "--hasta" in sys.argv:
        hasta = sys.argv[sys.argv.index("--hasta") + 1]

    print("=" * 66)
    print(" Generación de mediciones simuladas")
    print("=" * 66)

    if "--limpiar" in sys.argv:
        eliminadas = limpiar_simulados()
        print(f"  Se eliminaron {eliminadas} mediciones simuladas.")
        print(f"  Las mediciones efectivas (hasta {ULTIMO_PERIODO_REAL}) se conservan.")
        return

    print(f"  Mediciones efectivas : septiembre 2024 a marzo 2025 (fuente Jira)")
    print(f"  Períodos a completar : hasta {hasta}")
    print()

    generar(hasta, simular="--simular" in sys.argv)


if __name__ == "__main__":
    main()
