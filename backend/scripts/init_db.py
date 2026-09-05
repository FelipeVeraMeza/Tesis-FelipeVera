"""
Inicializacion de la base de datos.

Crea el esquema (tablas 17 a 23 del modelo logico), carga los datos semilla
—roles, usuarios, procesos criticos y fichas tecnicas de KPI— y genera los
hashes de contrasena.

Modo de uso:
    python backend/init_db.py            # crea esquema y datos
    python backend/init_db.py --verificar  # solo comprueba el estado actual

Requiere la variable SUPABASE_DB_PASSWORD en el archivo .env (contrasena de la
base de datos, disponible en Supabase > Project Settings > Database). Si no se
encuentra, el script imprime el SQL para pegarlo en el SQL Editor de Supabase.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, db  # noqa: E402
from app.auth import cifrar_contrasena  # noqa: E402

CONTRASENA_DEMO = "1234"


def _leer_sql() -> str:
    esquema = (config.SQL_DIR / "01_esquema.sql").read_text(encoding="utf-8")
    datos = (config.SQL_DIR / "02_datos_iniciales.sql").read_text(encoding="utf-8")
    # Los usuarios se insertan con un marcador; aqui se reemplaza por el hash real
    datos = datos.replace("__HASH__", cifrar_contrasena(CONTRASENA_DEMO))

    # RLS se aplica al final, una vez creadas las tablas (RNF3)
    seguridad = (config.SQL_DIR / "03_seguridad_rls.sql").read_text(encoding="utf-8")
    ampliacion = (config.SQL_DIR / "04_ampliacion_catalogo.sql").read_text(encoding="utf-8")
    notificaciones = (config.SQL_DIR / "05_notificaciones.sql").read_text(encoding="utf-8")
    incidencias = (config.SQL_DIR / "06_incidencias.sql").read_text(encoding="utf-8")

    return "\n\n".join(
        (esquema, datos, seguridad, ampliacion, notificaciones, incidencias)
    )


def _referencia_proyecto() -> str:
    """Identificador del proyecto, extraido de la URL de Supabase."""
    return config.SUPABASE_URL.split("//")[1].split(".")[0]


def _candidatos_conexion() -> list[dict]:
    """
    Parametros de conexion a probar, en orden.

    Supabase ofrece conexion directa y a traves del pooler; segun la red del
    equipo puede funcionar una u otra, por lo que se intentan ambas. La
    contrasena se pasa como parametro y no dentro de la URL, para no tener que
    escapar caracteres especiales.
    """
    password = os.getenv("SUPABASE_DB_PASSWORD", "")
    if not password:
        return []

    referencia = _referencia_proyecto()
    # La region del proyecto se toma del .env; el resto se prueba como respaldo
    region_configurada = os.getenv("SUPABASE_REGION", "aws-0-us-west-2")
    regiones = [region_configurada] + [
        r
        for r in ("aws-0-us-east-1", "aws-0-us-east-2", "aws-0-us-west-1", "aws-0-sa-east-1")
        if r != region_configurada
    ]

    # Se usa el pooler y no el host directo, porque este ultimo solo publica
    # direcciones IPv6 y muchas redes corporativas no las rutean.
    candidatos: list[dict] = []
    for region in regiones:
        for puerto in (5432, 6543):
            candidatos.append(
                {
                    "host": f"{region}.pooler.supabase.com",
                    "port": puerto,
                    "user": f"postgres.{referencia}",
                    "password": password,
                    "dbname": "postgres",
                    "sslmode": "require",
                }
            )
    return candidatos


def crear_via_postgres(sql: str) -> bool:
    candidatos = _candidatos_conexion()
    if not candidatos:
        return False

    try:
        import psycopg2
    except ImportError:
        print("  psycopg2 no esta instalado. Ejecute: pip install psycopg2-binary")
        return False

    conexion = None
    for parametros in candidatos:
        try:
            conexion = psycopg2.connect(**parametros, connect_timeout=12)
            print(f"  Conectado a PostgreSQL en {parametros['host']}:{parametros['port']}")
            break
        except Exception:  # noqa: BLE001, S112
            continue

    if conexion is None:
        print("  No se pudo establecer conexion directa con PostgreSQL.")
        return False

    try:
        conexion.autocommit = True
        with conexion.cursor() as cursor:
            cursor.execute(sql)
        print("  Esquema y datos creados correctamente.")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  Error al ejecutar el SQL: {exc}")
        return False
    finally:
        conexion.close()


def verificar() -> None:
    estado = db.probar_conexion()
    print(f"  Conexion a Supabase : {'OK' if estado['conectado'] else 'FALLIDA'}")
    if not estado["conectado"]:
        print(f"  Detalle: {estado.get('detalle')}")
        return

    print(f"  URL                 : {estado['url']}")
    if not estado.get("esquema_creado"):
        print("  Esquema             : NO CREADO")
        return

    print("  Esquema             : CREADO")
    for tabla in ("rol", "usuario", "proceso_ti", "indicador_kpi",
                  "meta_kpi", "resultado_kpi", "notificacion", "incidencia"):
        try:
            filas = db.seleccionar(tabla, {"select": "*"})
            print(f"    {tabla:<16} {len(filas):>4} registros")
        except db.ErrorBaseDatos as exc:
            print(f"    {tabla:<16} error: {exc}")

    verificar_seguridad()


def verificar_seguridad() -> None:
    """
    Comprueba que las tablas no sean accesibles con la clave publica (RNF3).

    Se intenta leer cada tabla usando la clave que viaja al navegador; si
    alguna responde con datos, el acceso anonimo esta abierto.
    """
    import requests

    clave_publica = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    if not clave_publica:
        return

    print()
    print("  Control de acceso anonimo (RLS)")

    expuestas = []
    for tabla in ("rol", "usuario", "proceso_ti", "fuente_dato",
                  "indicador_kpi", "meta_kpi", "resultado_kpi", "notificacion", "incidencia"):
        try:
            respuesta = requests.get(
                f"{config.SUPABASE_URL}/rest/v1/{tabla}",
                headers={
                    "apikey": clave_publica,
                    "Authorization": f"Bearer {clave_publica}",
                },
                params={"select": "*", "limit": 1},
                timeout=15,
            )
        except requests.RequestException:
            continue

        if respuesta.status_code == 200:
            expuestas.append(tabla)
            print(f"    {tabla:<16} EXPUESTA al acceso publico")
        else:
            print(f"    {tabla:<16} protegida")

    if expuestas:
        print()
        print("    Ejecute backend/sql/03_seguridad_rls.sql para cerrar el acceso.")


def main() -> None:
    config.validar_configuracion()

    print("=" * 62)
    print(" Inicializacion de la base de datos - Proyecto KPI")
    print("=" * 62)

    if "--verificar" in sys.argv:
        verificar()
        return

    estado = db.probar_conexion()
    if not estado["conectado"]:
        print(f"  No hay conexion con Supabase: {estado.get('detalle')}")
        sys.exit(1)
    print("  Conexion con Supabase establecida.")

    sql = _leer_sql()

    if crear_via_postgres(sql):
        print()
        verificar()
        print()
        print(f"  Usuarios de prueba (contrasena: {CONTRASENA_DEMO})")
        print("    gerente@horizonte.cl   - Gerente")
        print("    lider@horizonte.cl     - Lider de proceso")
        print("    analista@horizonte.cl  - Analista")
        print("    admin@horizonte.cl     - Administrador")
        return

    # Alternativa: dejar el SQL listo para el editor web de Supabase
    salida = config.SQL_DIR / "instalar_completo.sql"
    salida.write_text(sql, encoding="utf-8")
    print()
    print("  No fue posible ejecutar el SQL automaticamente.")
    print("  Se genero el archivo:")
    print(f"    {salida}")
    print()
    print("  Pasos manuales:")
    print("   1. Abra https://supabase.com/dashboard  >  su proyecto  >  SQL Editor")
    print("   2. Pegue el contenido completo de ese archivo y presione Run")
    print("   3. Vuelva a ejecutar: python backend/init_db.py --verificar")
    print()
    print("  Alternativa automatica: agregue SUPABASE_DB_PASSWORD al archivo .env")
    print("  (Supabase > Project Settings > Database > Database password).")


if __name__ == "__main__":
    main()
