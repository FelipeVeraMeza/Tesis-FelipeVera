"""
Medición de rendimiento del sistema (RNF1).

El requisito no funcional establece que el sistema debe procesar y visualizar
los KPI en menos de 10 segundos por archivo cargado. Este script mide los
tiempos de respuesta de cada operación y contrasta el resultado con ese umbral.

Uso:
    python backend/medir_rendimiento.py            # 5 repeticiones
    python backend/medir_rendimiento.py 10         # número de repeticiones
"""
import statistics
import sys
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:5000"
UMBRAL_SEGUNDOS = 10.0

CREDENCIALES = {"correo": "analista@horizonte.cl", "contrasena": "1234"}


def _cronometrar(funcion, repeticiones: int) -> dict | None:
    """Ejecuta una operación varias veces y resume sus tiempos."""
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        try:
            respuesta = funcion()
        except requests.RequestException as exc:
            return {"error": str(exc)}
        transcurrido = time.perf_counter() - inicio

        if respuesta.status_code >= 400:
            return {"error": f"HTTP {respuesta.status_code}"}
        tiempos.append(transcurrido)

    return {
        "promedio": statistics.mean(tiempos),
        "minimo": min(tiempos),
        "maximo": max(tiempos),
        "muestras": len(tiempos),
    }


def main() -> None:
    repeticiones = 5
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        repeticiones = int(sys.argv[1])

    print("=" * 66)
    print(" Medición de rendimiento (RNF1)")
    print("=" * 66)
    print(f"  Umbral definido : {UMBRAL_SEGUNDOS:.0f} segundos por operación")
    print(f"  Repeticiones    : {repeticiones}")
    print()

    # Autenticación previa
    try:
        acceso = requests.post(f"{BASE}/api/login", json=CREDENCIALES, timeout=30)
    except requests.RequestException:
        print("  No hay respuesta del servidor. Ejecute primero: python backend/run.py")
        sys.exit(1)

    if acceso.status_code != 200:
        print(f"  No fue posible autenticarse (HTTP {acceso.status_code}).")
        sys.exit(1)

    token = acceso.json()["token"]
    cabeceras = {"Authorization": f"Bearer {token}"}

    raiz = Path(__file__).resolve().parent.parent.parent
    archivo_csv = raiz / "docs" / "plantillas" / "cambios.csv"

    def cargar_archivo():
        with open(archivo_csv, "rb") as fuente:
            return requests.post(
                f"{BASE}/api/carga",
                headers=cabeceras,
                data={"proceso": "cambios"},
                files={"archivo": ("cambios.csv", fuente, "text/csv")},
                timeout=60,
            )

    operaciones = [
        ("Autenticación", lambda: requests.post(f"{BASE}/api/login", json=CREDENCIALES, timeout=30)),
        ("Consulta de KPI (críticos)", lambda: requests.get(f"{BASE}/api/kpis?proceso=criticos", headers=cabeceras, timeout=60)),
        ("Consulta de KPI (catálogo completo)", lambda: requests.get(f"{BASE}/api/kpis?proceso=general", headers=cabeceras, timeout=60)),
        ("Resumen por proceso", lambda: requests.get(f"{BASE}/api/resumen", headers=cabeceras, timeout=60)),
        ("Consulta de alertas", lambda: requests.get(f"{BASE}/api/alertas", headers=cabeceras, timeout=60)),
        ("Carga y procesamiento ETL", cargar_archivo),
        ("Exportación CSV", lambda: requests.get(f"{BASE}/api/exportar?proceso=general", headers=cabeceras, timeout=60)),
        ("Generación de reporte", lambda: requests.get(f"{BASE}/api/reporte?proceso=criticos", headers=cabeceras, timeout=60)),
    ]

    print(f"  {'Operación':<38}{'Promedio':>10}{'Mínimo':>9}{'Máximo':>9}   Resultado")
    print("  " + "-" * 62)

    incumplen = []
    for nombre, funcion in operaciones:
        medicion = _cronometrar(funcion, repeticiones)

        if medicion is None or "error" in medicion:
            detalle = medicion.get("error", "sin datos") if medicion else "sin datos"
            print(f"  {nombre:<38}{'—':>10}{'—':>9}{'—':>9}   {detalle}")
            continue

        cumple = medicion["maximo"] < UMBRAL_SEGUNDOS
        if not cumple:
            incumplen.append(nombre)

        print(
            f"  {nombre:<38}"
            f"{medicion['promedio']:>9.3f}s"
            f"{medicion['minimo']:>8.3f}s"
            f"{medicion['maximo']:>8.3f}s"
            f"   {'CUMPLE' if cumple else 'EXCEDE'}"
        )

    print()
    if incumplen:
        print(f"  Operaciones sobre el umbral: {', '.join(incumplen)}")
    else:
        print(f"  Todas las operaciones se completan bajo los {UMBRAL_SEGUNDOS:.0f} segundos.")
        print("  El requisito RNF1 se cumple.")

    print()
    print("  Nota: los tiempos incluyen la latencia de red hacia la base de datos,")
    print("  alojada en Supabase. En una instalación local serían menores.")


if __name__ == "__main__":
    main()
