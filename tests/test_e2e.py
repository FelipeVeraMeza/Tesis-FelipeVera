"""
Pruebas de integración y de extremo a extremo.

A diferencia del resto de la batería, estas pruebas se ejecutan contra un
servidor en funcionamiento y una base de datos real. Verifican que las capas
del sistema operen correctamente entre sí y que los flujos completos —tal como
los recorre un usuario— produzcan el resultado esperado.

Requieren el servidor en ejecución:

    python backend/run.py
    python -m pytest tests/test_e2e.py

Si el servidor no responde, las pruebas se omiten en lugar de fallar, de modo
que la batería principal siga siendo ejecutable sin conexión.
"""
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

BASE = "http://127.0.0.1:5000"
TIEMPO_LIMITE = 30

CREDENCIALES = {
    "gerente": {"correo": "gerente@horizonte.cl", "contrasena": "1234"},
    "lider": {"correo": "lider@horizonte.cl", "contrasena": "1234"},
    "analista": {"correo": "analista@horizonte.cl", "contrasena": "1234"},
    "admin": {"correo": "admin@horizonte.cl", "contrasena": "1234"},
}


def _servidor_disponible() -> bool:
    try:
        return requests.get(f"{BASE}/api/salud", timeout=5).status_code == 200
    except requests.RequestException:
        return False


# Toda la batería depende de que el servidor esté operativo
pytestmark = pytest.mark.skipif(
    not _servidor_disponible(),
    reason="El servidor no responde en http://127.0.0.1:5000",
)


@pytest.fixture(scope="module")
def sesiones():
    """Token de cada perfil, obtenido una sola vez para toda la batería."""
    tokens = {}
    for perfil, credenciales in CREDENCIALES.items():
        respuesta = requests.post(f"{BASE}/api/login", json=credenciales, timeout=TIEMPO_LIMITE)
        if respuesta.status_code == 200:
            tokens[perfil] = respuesta.json()["token"]
    return tokens


def cabeceras(sesiones, perfil="gerente"):
    return {"Authorization": f"Bearer {sesiones[perfil]}"}


def _limpiar_periodo(periodo: str) -> None:
    """
    Elimina las mediciones de un período de prueba.

    Las pruebas que escriben en la base deben dejarla como la encontraron: de
    lo contrario, los datos de prueba se mezclarían con las mediciones reales
    del catálogo.
    """
    try:
        from app import config, db  # noqa: F401

        requests.delete(
            f"{config.SUPABASE_URL}/rest/v1/resultado_kpi",
            headers={
                "apikey": config.SUPABASE_SECRET_KEY,
                "Authorization": f"Bearer {config.SUPABASE_SECRET_KEY}",
            },
            params={"periodo": f"eq.{periodo}"},
            timeout=TIEMPO_LIMITE,
        )
    except Exception:  # noqa: BLE001
        # La limpieza es complementaria: su fallo no invalida la prueba
        pass


# ==================================================================
# Integración entre capas
# ==================================================================
class TestIntegracion:
    """La aplicación, la lógica de negocio y la base de datos operan juntas."""

    def test_la_base_responde_y_tiene_esquema(self):
        datos = requests.get(f"{BASE}/api/salud", timeout=TIEMPO_LIMITE).json()

        assert datos["conectado"] is True
        assert datos["esquema_creado"] is True

    def test_el_catalogo_esta_cargado(self, sesiones):
        indicadores = requests.get(
            f"{BASE}/api/kpis", headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE
        ).json()

        assert len(indicadores) > 0, "El catálogo de indicadores está vacío"

    def test_los_procesos_criticos_estan_marcados(self, sesiones):
        """Los cuatro procesos del alcance deben estar identificados."""
        procesos = requests.get(
            f"{BASE}/api/procesos", headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE
        ).json()

        criticos = [p["codigo_proceso"] for p in procesos if p["critico"]]

        assert set(criticos) == {"cambios", "incidentes", "requerimientos", "demanda"}

    def test_cada_indicador_pertenece_a_un_proceso_existente(self, sesiones):
        """Verifica la integridad referencial a través de la API."""
        indicadores = requests.get(
            f"{BASE}/api/kpis", headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE
        ).json()
        procesos = requests.get(
            f"{BASE}/api/procesos", headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE
        ).json()

        codigos = {p["codigo_proceso"] for p in procesos}

        for indicador in indicadores:
            assert indicador["proceso"] in codigos, (
                f"El indicador «{indicador['nombre']}» referencia un proceso inexistente"
            )

    def test_el_historico_esta_ordenado_cronologicamente(self, sesiones):
        indicadores = requests.get(
            f"{BASE}/api/kpis", headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE
        ).json()

        for indicador in indicadores:
            periodos = [p["periodo"] for p in indicador["historico"]]
            assert periodos == sorted(periodos), (
                f"La serie de «{indicador['nombre']}» no está ordenada"
            )

    def test_el_valor_actual_corresponde_a_la_ultima_medicion(self, sesiones):
        indicadores = requests.get(
            f"{BASE}/api/kpis", headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE
        ).json()

        for indicador in indicadores:
            if indicador["historico"]:
                assert indicador["valor"] == indicador["historico"][-1]["valor"]
            else:
                assert indicador["valor"] is None


# ==================================================================
# Consistencia de los datos presentados
# ==================================================================
class TestConsistencia:
    """Las distintas vistas del sistema deben concordar entre sí."""

    def test_las_alertas_coinciden_con_los_indicadores_desviados(self, sesiones):
        indicadores = requests.get(
            f"{BASE}/api/kpis", headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE
        ).json()
        alertas = requests.get(
            f"{BASE}/api/alertas", headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE
        ).json()

        desviados = {k["id_kpi"] for k in indicadores if k["estado"] in ("riesgo", "bajo")}
        alertados = {a["id_kpi"] for a in alertas}

        assert desviados == alertados

    def test_el_resumen_concuerda_con_el_detalle(self, sesiones):
        indicadores = requests.get(
            f"{BASE}/api/kpis", headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE
        ).json()
        resumen = requests.get(
            f"{BASE}/api/resumen", headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE
        ).json()

        for bloque in resumen:
            del_proceso = [k for k in indicadores if k["proceso"] == bloque["proceso"]]
            medidos = [k for k in del_proceso if k["estado"] != "sin_datos"]

            assert bloque["total_kpis"] == len(del_proceso)
            assert bloque["kpis_medidos"] == len(medidos)

    def test_el_estado_general_concuerda_con_el_detalle(self, sesiones):
        general = requests.get(
            f"{BASE}/api/estado-general?proceso=criticos",
            headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE,
        ).json()
        indicadores = requests.get(
            f"{BASE}/api/kpis?proceso=criticos",
            headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE,
        ).json()

        medidos = [k for k in indicadores if k["estado"] != "sin_datos"]

        assert general["indicadores_totales"] == len(indicadores)
        assert general["indicadores_medidos"] == len(medidos)

    def test_un_indicador_sin_datos_no_declara_cumplimiento(self, sesiones):
        """Un indicador no medido no debe presentarse como si rindiera cero."""
        indicadores = requests.get(
            f"{BASE}/api/kpis", headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE
        ).json()

        for indicador in indicadores:
            if indicador["estado"] == "sin_datos":
                assert indicador["valor"] is None
                assert indicador["cumplimiento"] is None

    def test_la_evolucion_cubre_los_periodos_registrados(self, sesiones):
        evolucion = requests.get(
            f"{BASE}/api/evolucion?proceso=criticos",
            headers=cabeceras(sesiones), timeout=TIEMPO_LIMITE,
        ).json()

        periodos = [p["periodo"] for p in evolucion]

        assert periodos == sorted(periodos)
        assert all(0 <= p["cumplimiento"] <= 100 for p in evolucion)


# ==================================================================
# Flujos completos
# ==================================================================
class TestFlujos:
    """Recorridos equivalentes a los que realiza un usuario."""

    def test_flujo_del_gerente(self, sesiones):
        """Ingresar, revisar el estado general y consultar las alertas."""
        acceso = requests.post(
            f"{BASE}/api/login", json=CREDENCIALES["gerente"], timeout=TIEMPO_LIMITE
        )
        assert acceso.status_code == 200

        token = acceso.json()["token"]
        cabecera = {"Authorization": f"Bearer {token}"}

        general = requests.get(
            f"{BASE}/api/estado-general?proceso=criticos", headers=cabecera, timeout=TIEMPO_LIMITE
        )
        assert general.status_code == 200

        alertas = requests.get(f"{BASE}/api/alertas", headers=cabecera, timeout=TIEMPO_LIMITE)
        assert alertas.status_code == 200

        # Desde una alerta se accede al detalle del indicador
        if alertas.json():
            id_kpi = alertas.json()[0]["id_kpi"]
            indicadores = requests.get(
                f"{BASE}/api/kpis", headers=cabecera, timeout=TIEMPO_LIMITE
            ).json()
            assert any(k["id_kpi"] == id_kpi for k in indicadores)

    def test_flujo_de_carga_del_analista(self, sesiones):
        """
        Cargar un archivo y comprobar que queda registrado.

        La prueba usa un período muy posterior al de las mediciones reales,
        de modo que no altere la serie histórica del catálogo, y lo elimina
        al finalizar.
        """
        import io

        cabecera = cabeceras(sesiones, "analista")

        # Período reservado para pruebas, fuera del rango de los datos reales
        periodo = "2099-01"
        contenido = (
            "periodo,cambios_solicitados,cambios_aceptados,cambios_urgentes,"
            "cambios_implementados,cambios_revertidos,cambios_error_certificacion\n"
            f"{periodo},100,95,10,90,2,3\n"
        )

        try:
            carga = requests.post(
                f"{BASE}/api/carga",
                headers=cabecera,
                data={"proceso": "cambios"},
                files={"archivo": ("prueba_e2e.csv", io.BytesIO(contenido.encode()), "text/csv")},
                timeout=60,
            )

            assert carga.status_code == 200

            resultado = carga.json()
            assert resultado["resultados_registrados"] > 0
            assert resultado["responsable"], "La carga debe registrar su responsable"
            assert periodo in resultado["periodos_procesados"]

            # La trazabilidad queda disponible en el historial
            historial = requests.get(
                f"{BASE}/api/cargas", headers=cabecera, timeout=TIEMPO_LIMITE
            ).json()

            assert historial[0]["archivo"] == "prueba_e2e.csv"
            assert historial[0]["responsable"] == resultado["responsable"]

        finally:
            _limpiar_periodo(periodo)

    def test_flujo_de_exportacion(self, sesiones):
        cabecera = cabeceras(sesiones)

        csv = requests.get(
            f"{BASE}/api/exportar?proceso=criticos", headers=cabecera, timeout=60
        )
        assert csv.status_code == 200
        assert "Proceso;KPI" in csv.text

        pdf = requests.get(
            f"{BASE}/api/reporte.pdf?proceso=criticos", headers=cabecera, timeout=60
        )
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

    def test_flujo_de_incidencias(self, sesiones):
        cabecera = cabeceras(sesiones, "analista")

        registro = requests.post(
            f"{BASE}/api/incidencias",
            headers=cabecera,
            json={
                "modulo": "Dashboard",
                "severidad": "Baja",
                "titulo": "Prueba automatizada de registro",
                "descripcion": "Incidencia generada por la bateria de pruebas E2E.",
            },
            timeout=TIEMPO_LIMITE,
        )

        assert registro.status_code == 201
        identificador = registro.json()["id_incidencia"]

        listado = requests.get(
            f"{BASE}/api/incidencias", headers=cabecera, timeout=TIEMPO_LIMITE
        ).json()

        assert any(i["id_incidencia"] == identificador for i in listado)


# ==================================================================
# Control de acceso extremo a extremo
# ==================================================================
class TestSeguridad:
    def test_cada_perfil_recibe_sus_atribuciones(self, sesiones):
        esperado = {
            "gerente": {"puede_cargar": False, "puede_notificar": True},
            "lider": {"puede_cargar": False, "puede_notificar": True},
            "analista": {"puede_cargar": True, "puede_notificar": False},
            "admin": {"puede_cargar": True, "puede_notificar": True},
        }

        for perfil, credenciales in CREDENCIALES.items():
            datos = requests.post(
                f"{BASE}/api/login", json=credenciales, timeout=TIEMPO_LIMITE
            ).json()
            permisos = datos["usuario"]["permisos"]

            for atribucion, valor in esperado[perfil].items():
                assert permisos[atribucion] is valor, (
                    f"El perfil {perfil} no tiene la atribución {atribucion} esperada"
                )

    def test_la_contrasena_nunca_se_devuelve(self, sesiones):
        """Ninguna respuesta debe exponer credenciales."""
        datos = requests.post(
            f"{BASE}/api/login", json=CREDENCIALES["gerente"], timeout=TIEMPO_LIMITE
        ).json()

        assert "contrasena" not in str(datos).lower()

    def test_credenciales_incorrectas(self):
        respuesta = requests.post(
            f"{BASE}/api/login",
            json={"correo": "gerente@horizonte.cl", "contrasena": "incorrecta"},
            timeout=TIEMPO_LIMITE,
        )
        assert respuesta.status_code == 401

    def test_usuario_inexistente(self):
        respuesta = requests.post(
            f"{BASE}/api/login",
            json={"correo": "desconocido@horizonte.cl", "contrasena": "1234"},
            timeout=TIEMPO_LIMITE,
        )
        assert respuesta.status_code == 401

    def test_el_analista_no_accede_a_operaciones_de_gerencia(self, sesiones):
        respuesta = requests.post(
            f"{BASE}/api/notificar",
            headers=cabeceras(sesiones, "analista"),
            json={"id_kpi": 1},
            timeout=TIEMPO_LIMITE,
        )
        assert respuesta.status_code == 403

    def test_el_gerente_no_accede_a_operaciones_de_carga(self, sesiones):
        respuesta = requests.post(
            f"{BASE}/api/carga",
            headers=cabeceras(sesiones, "gerente"),
            data={"proceso": "cambios"},
            timeout=TIEMPO_LIMITE,
        )
        assert respuesta.status_code == 403


# ==================================================================
# Interfaz web
# ==================================================================
class TestInterfaz:
    @pytest.mark.parametrize(
        "recurso",
        [
            "/",
            "/login.html",
            "/dashboard.html",
            "/css/base.css",
            "/css/dashboard.css",
            "/css/login.css",
            "/js/api.js",
            "/js/dashboard.js",
            "/js/login.js",
            "/assets/logoAFPhorizonte.png",
        ],
    )
    def test_los_recursos_se_entregan(self, recurso):
        respuesta = requests.get(f"{BASE}{recurso}", timeout=TIEMPO_LIMITE)
        assert respuesta.status_code == 200
        assert len(respuesta.content) > 0

    def test_el_panel_declara_sus_vistas(self):
        """La interfaz debe incluir las seis vistas de análisis."""
        html = requests.get(f"{BASE}/dashboard.html", timeout=TIEMPO_LIMITE).text

        for vista in ("resumen", "procesos", "indicadores", "tendencias", "alertas", "reportes"):
            assert f'data-vista="{vista}"' in html, f"Falta la vista {vista}"
            assert f'id="vista-{vista}"' in html


# ==================================================================
# Rendimiento (RNF1)
# ==================================================================
class TestRendimiento:
    """El requisito establece un umbral de 10 segundos por operación."""

    UMBRAL = 10.0

    @pytest.mark.parametrize(
        "ruta",
        [
            "/api/kpis?proceso=criticos",
            "/api/kpis?proceso=general",
            "/api/resumen",
            "/api/alertas",
            "/api/estado-general?proceso=criticos",
            "/api/evolucion?proceso=criticos",
        ],
    )
    def test_tiempo_de_respuesta(self, sesiones, ruta):
        import time

        inicio = time.perf_counter()
        respuesta = requests.get(f"{BASE}{ruta}", headers=cabeceras(sesiones), timeout=60)
        transcurrido = time.perf_counter() - inicio

        assert respuesta.status_code == 200
        assert transcurrido < self.UMBRAL, (
            f"{ruta} demoró {transcurrido:.2f} s, sobre el umbral de {self.UMBRAL} s"
        )

    def test_generacion_del_reporte(self, sesiones):
        import time

        inicio = time.perf_counter()
        respuesta = requests.get(
            f"{BASE}/api/reporte.pdf?proceso=general",
            headers=cabeceras(sesiones), timeout=60,
        )
        transcurrido = time.perf_counter() - inicio

        assert respuesta.status_code == 200
        assert transcurrido < self.UMBRAL


# ==================================================================
# Concurrencia
# ==================================================================
class TestConcurrencia:
    def test_consultas_simultaneas(self, sesiones):
        """Varias consultas en paralelo deben resolverse correctamente."""
        from concurrent.futures import ThreadPoolExecutor

        def consultar(_):
            return requests.get(
                f"{BASE}/api/kpis?proceso=criticos",
                headers=cabeceras(sesiones), timeout=60,
            ).status_code

        with ThreadPoolExecutor(max_workers=6) as ejecutor:
            codigos = list(ejecutor.map(consultar, range(6)))

        assert all(codigo == 200 for codigo in codigos)

    def test_sesiones_simultaneas_de_distintos_perfiles(self, sesiones):
        from concurrent.futures import ThreadPoolExecutor

        def consultar(perfil):
            return requests.get(
                f"{BASE}/api/sesion", headers=cabeceras(sesiones, perfil), timeout=60
            ).json()["rol"]

        with ThreadPoolExecutor(max_workers=4) as ejecutor:
            roles = list(ejecutor.map(consultar, CREDENCIALES))

        # Cada sesión conserva su propia identidad
        assert set(roles) == {"Gerente", "Lider", "Analista", "Administrador"}
