"""
Pruebas de la API REST.

Verifican los endpoints en su contrato completo: códigos de respuesta,
estructura de los datos devueltos, control de acceso por perfil y manejo de
solicitudes mal formadas.

Las pruebas se ejecutan sobre el cliente de pruebas de Flask, con la capa de
acceso a datos sustituida por datos controlados, de modo que no dependen de la
disponibilidad de la base de datos.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import auth  # noqa: E402


# ==================================================================
# Datos de prueba
# ==================================================================
PROCESOS = [
    {
        "id_proceso": 1,
        "nombre_proceso": "Gestion de Cambios TI",
        "codigo_proceso": "cambios",
        "descripcion": "Control de cambios",
        "responsable": "Lider de Cambios",
        "estado": "Activo",
        "critico": True,
    },
    {
        "id_proceso": 2,
        "nombre_proceso": "Gestion de Calidad TI",
        "codigo_proceso": "calidad",
        "descripcion": "Aseguramiento de calidad",
        "responsable": "Lider de Calidad",
        "estado": "Activo",
        "critico": False,
    },
]

INDICADORES = [
    {
        "id_kpi": 1,
        "codigo_kpi": "cam_urgentes",
        "nombre_kpi": "Porcentaje de cambios urgentes",
        "descripcion": "Cambios urgentes sobre el total",
        "formula": "(Urgentes / Total) * 100",
        "unidad_medida": "%",
        "periodicidad": "Mensual",
        "id_proceso": 1,
        "valor_minimo": 0,
        "valor_maximo": 100,
        "meta": 30,
        "tipo_medicion": 2,
        "tipo_grafico": 1,
        "estado": "Implementado",
        "viable": "Si",
        "dueno_proceso": "Sebastian Rojas",
        "fuente_origen": "Jira",
        "perspectiva": None,
    },
    {
        "id_kpi": 2,
        "codigo_kpi": "cam_sla",
        "nombre_kpi": "Cumplimiento de SLA",
        "descripcion": "Solicitudes dentro del plazo",
        "formula": "(Dentro de SLA / Total) * 100",
        "unidad_medida": "%",
        "periodicidad": "Mensual",
        "id_proceso": 1,
        "valor_minimo": 0,
        "valor_maximo": 100,
        "meta": 90,
        "tipo_medicion": 1,
        "tipo_grafico": 1,
        "estado": "Implementado",
        "viable": "Si",
        "dueno_proceso": "Karla",
        "fuente_origen": "Jira",
        "perspectiva": None,
    },
    {
        "id_kpi": 3,
        "codigo_kpi": "cal_pendiente",
        "nombre_kpi": "Indicador sin instrumentar",
        "descripcion": "Aun no se mide",
        "formula": "",
        "unidad_medida": "%",
        "periodicidad": "Mensual",
        "id_proceso": 2,
        "valor_minimo": 0,
        "valor_maximo": 100,
        "meta": 80,
        "tipo_medicion": 1,
        "tipo_grafico": 1,
        "estado": "No implementado",
        "viable": "No",
        "dueno_proceso": None,
        "fuente_origen": None,
        "perspectiva": None,
    },
]

# El primer indicador cumple su meta; el segundo se encuentra muy por debajo
RESULTADOS = [
    {"id_kpi": 1, "valor_real": 28.0, "fecha_registro": "2025-01-01", "periodo": "2025-01"},
    {"id_kpi": 1, "valor_real": 20.0, "fecha_registro": "2025-02-01", "periodo": "2025-02"},
    {"id_kpi": 1, "valor_real": 12.0, "fecha_registro": "2025-03-01", "periodo": "2025-03"},
    {"id_kpi": 2, "valor_real": 40.0, "fecha_registro": "2025-01-01", "periodo": "2025-01"},
    {"id_kpi": 2, "valor_real": 35.0, "fecha_registro": "2025-02-01", "periodo": "2025-02"},
    {"id_kpi": 2, "valor_real": 30.0, "fecha_registro": "2025-03-01", "periodo": "2025-03"},
]

USUARIOS = {
    "gerente@horizonte.cl": ("Gerente de TI", "Gerente", 1),
    "lider@horizonte.cl": ("Lider de Proceso", "Lider", 2),
    "analista@horizonte.cl": ("Analista de Proceso", "Analista", 3),
    "admin@horizonte.cl": ("Administrador TI", "Administrador", 4),
}


# ==================================================================
# Preparación
# ==================================================================
@pytest.fixture
def app(monkeypatch):
    """Aplicación Flask con la capa de datos sustituida."""
    from app import api, db

    def seleccionar(tabla, params=None):
        return {
            "proceso_ti": PROCESOS,
            "indicador_kpi": INDICADORES,
            "resultado_kpi": RESULTADOS,
            "notificacion": [],
            "incidencia": [],
            "fuente_dato": [],
        }.get(tabla, [])

    monkeypatch.setattr(db, "seleccionar", seleccionar)
    monkeypatch.setattr(db, "insertar", lambda tabla, registros: [{"id_incidencia": 1, "id_notificacion": 1}])
    monkeypatch.setattr(db, "probar_conexion", lambda: {"conectado": True, "esquema_creado": True, "url": "https://prueba"})

    aplicacion = api.crear_app()
    aplicacion.config["TESTING"] = True
    return aplicacion


@pytest.fixture
def cliente(app):
    return app.test_client()


def _token(correo: str) -> str:
    nombre, rol, identificador = USUARIOS[correo]
    return auth.generar_token(
        {
            "id_usuario": identificador,
            "correo": correo,
            "nombre_usuario": nombre,
            "rol": rol,
        }
    )


@pytest.fixture
def cabeceras_gerente():
    return {"Authorization": f"Bearer {_token('gerente@horizonte.cl')}"}


@pytest.fixture
def cabeceras_analista():
    return {"Authorization": f"Bearer {_token('analista@horizonte.cl')}"}


# ==================================================================
# Estado del servicio
# ==================================================================
class TestSalud:
    def test_no_requiere_autenticacion(self, cliente):
        """El estado del servicio debe poder consultarse sin sesión."""
        respuesta = cliente.get("/api/salud")

        assert respuesta.status_code == 200
        assert respuesta.get_json()["conectado"] is True


# ==================================================================
# Control de acceso
# ==================================================================
class TestAutenticacion:
    @pytest.mark.parametrize(
        "ruta",
        [
            "/api/kpis",
            "/api/resumen",
            "/api/alertas",
            "/api/procesos",
            "/api/estado-general",
            "/api/evolucion",
            "/api/periodos",
            "/api/sesion",
        ],
    )
    def test_los_endpoints_exigen_sesion(self, cliente, ruta):
        assert cliente.get(ruta).status_code == 401

    def test_un_token_invalido_se_rechaza(self, cliente):
        respuesta = cliente.get(
            "/api/kpis", headers={"Authorization": "Bearer token-falso"}
        )
        assert respuesta.status_code == 401

    def test_credenciales_incompletas(self, cliente):
        respuesta = cliente.post("/api/login", json={"correo": "gerente@horizonte.cl"})
        assert respuesta.status_code == 400

    def test_la_sesion_devuelve_el_perfil(self, cliente, cabeceras_gerente):
        datos = cliente.get("/api/sesion", headers=cabeceras_gerente).get_json()

        assert datos["rol"] == "Gerente"
        assert datos["correo"] == "gerente@horizonte.cl"


# ==================================================================
# Consulta de indicadores
# ==================================================================
class TestIndicadores:
    def test_estructura_de_la_respuesta(self, cliente, cabeceras_gerente):
        indicadores = cliente.get("/api/kpis", headers=cabeceras_gerente).get_json()

        assert isinstance(indicadores, list)
        esperados = {
            "id_kpi", "nombre", "valor", "meta", "estado", "unidad",
            "tendencia", "historico", "proceso", "proceso_nombre",
        }
        assert esperados <= set(indicadores[0])

    def test_filtro_por_proceso(self, cliente, cabeceras_gerente):
        indicadores = cliente.get(
            "/api/kpis?proceso=cambios", headers=cabeceras_gerente
        ).get_json()

        assert len(indicadores) == 2
        assert all(k["proceso"] == "cambios" for k in indicadores)

    def test_filtro_por_procesos_criticos(self, cliente, cabeceras_gerente):
        """El conjunto 'criticos' agrupa los procesos del alcance."""
        indicadores = cliente.get(
            "/api/kpis?proceso=criticos", headers=cabeceras_gerente
        ).get_json()

        assert all(k["proceso_critico"] for k in indicadores)

    def test_proceso_inexistente(self, cliente, cabeceras_gerente):
        indicadores = cliente.get(
            "/api/kpis?proceso=inexistente", headers=cabeceras_gerente
        ).get_json()

        assert indicadores == []

    def test_un_indicador_sin_mediciones_no_reporta_valor(self, cliente, cabeceras_gerente):
        indicadores = cliente.get("/api/kpis", headers=cabeceras_gerente).get_json()
        pendiente = next(k for k in indicadores if k["id_kpi"] == 3)

        assert pendiente["estado"] == "sin_datos"
        assert pendiente["valor"] is None
        assert pendiente["historico"] == []


# ==================================================================
# Síntesis del desempeño
# ==================================================================
class TestEstadoGeneral:
    def test_estructura(self, cliente, cabeceras_gerente):
        datos = cliente.get("/api/estado-general", headers=cabeceras_gerente).get_json()

        esperados = {
            "cumplimiento_global", "indicadores_totales", "indicadores_medidos",
            "indicadores_cumplen", "indicadores_desviados", "procesos_totales",
            "periodo_actual", "periodos",
        }
        assert esperados <= set(datos)

    def test_los_indicadores_sin_datos_no_se_cuentan_como_medidos(self, cliente, cabeceras_gerente):
        datos = cliente.get("/api/estado-general", headers=cabeceras_gerente).get_json()

        assert datos["indicadores_totales"] == 3
        assert datos["indicadores_medidos"] == 2

    def test_identifica_las_desviaciones(self, cliente, cabeceras_gerente):
        """El indicador 2 está en 30 % frente a una meta de 90 %."""
        datos = cliente.get("/api/estado-general", headers=cabeceras_gerente).get_json()

        assert datos["indicadores_desviados"] >= 1

    def test_el_periodo_actual_es_el_mas_reciente(self, cliente, cabeceras_gerente):
        datos = cliente.get("/api/estado-general", headers=cabeceras_gerente).get_json()

        assert datos["periodo_actual"] == "2025-03"
        assert datos["periodos"][0] == "2025-03"


# ==================================================================
# Evolución del cumplimiento
# ==================================================================
class TestEvolucion:
    def test_devuelve_un_punto_por_periodo(self, cliente, cabeceras_gerente):
        serie = cliente.get("/api/evolucion", headers=cabeceras_gerente).get_json()

        assert len(serie) == 3
        assert [p["periodo"] for p in serie] == ["2025-01", "2025-02", "2025-03"]

    def test_estructura_de_cada_punto(self, cliente, cabeceras_gerente):
        serie = cliente.get("/api/evolucion", headers=cabeceras_gerente).get_json()

        assert {"periodo", "cumplimiento", "indicadores"} <= set(serie[0])
        assert 0 <= serie[0]["cumplimiento"] <= 100


# ==================================================================
# Alertas
# ==================================================================
class TestAlertas:
    def test_solo_incluye_indicadores_desviados(self, cliente, cabeceras_gerente):
        alertas = cliente.get("/api/alertas", headers=cabeceras_gerente).get_json()

        assert all(a["estado"] in ("riesgo", "bajo") for a in alertas)

    def test_cada_alerta_permite_identificar_su_indicador(self, cliente, cabeceras_gerente):
        """El identificador es necesario para notificar y para el drill-down."""
        alertas = cliente.get("/api/alertas", headers=cabeceras_gerente).get_json()

        assert all("id_kpi" in a for a in alertas)
        assert all("dueno_proceso" in a for a in alertas)

    def test_las_alertas_siguen_el_proceso_seleccionado(self, cliente, cabeceras_gerente):
        """
        El panel comparte un mismo contexto de filtros: las alertas deben
        corresponder al proceso consultado y no al catálogo completo.
        """
        del_proceso = cliente.get(
            "/api/alertas?proceso=calidad", headers=cabeceras_gerente
        ).get_json()

        assert all(a["proceso"] == "Gestion de Calidad TI" for a in del_proceso)

    def test_un_proceso_sin_desviaciones_no_devuelve_alertas(self, cliente, cabeceras_gerente):
        alertas = cliente.get(
            "/api/alertas?proceso=inexistente", headers=cabeceras_gerente
        ).get_json()

        assert alertas == []

    def test_cada_alerta_informa_los_antecedentes_de_la_desviacion(
        self, cliente, cabeceras_gerente
    ):
        """
        La tarjeta de alerta muestra la brecha y la tendencia sin requerir
        una consulta adicional.
        """
        alertas = cliente.get("/api/alertas", headers=cabeceras_gerente).get_json()

        for alerta in alertas:
            assert {"brecha", "periodos", "direccion", "confiabilidad"} <= set(alerta)
            assert isinstance(alerta["periodos"], int)


# ==================================================================
# Notificaciones (RF7)
# ==================================================================
class TestNotificaciones:
    def test_el_analista_no_puede_notificar(self, cliente, cabeceras_analista):
        respuesta = cliente.post(
            "/api/notificar", json={"id_kpi": 2}, headers=cabeceras_analista
        )
        assert respuesta.status_code == 403

    def test_sin_identificador(self, cliente, cabeceras_gerente):
        respuesta = cliente.post("/api/notificar", json={}, headers=cabeceras_gerente)
        assert respuesta.status_code == 400

    def test_identificador_no_numerico(self, cliente, cabeceras_gerente):
        respuesta = cliente.post(
            "/api/notificar", json={"id_kpi": "dos"}, headers=cabeceras_gerente
        )
        assert respuesta.status_code == 400

    def test_indicador_inexistente(self, cliente, cabeceras_gerente):
        respuesta = cliente.post(
            "/api/notificar", json={"id_kpi": 9999}, headers=cabeceras_gerente
        )
        assert respuesta.status_code == 422

    def test_no_se_notifica_un_indicador_que_cumple(self, cliente, cabeceras_gerente):
        """El indicador 1 se encuentra dentro de su meta."""
        respuesta = cliente.post(
            "/api/notificar", json={"id_kpi": 1}, headers=cabeceras_gerente
        )
        assert respuesta.status_code == 422


# ==================================================================
# Carga de archivos (RF1)
# ==================================================================
class TestCarga:
    def test_el_gerente_no_carga_archivos(self, cliente, cabeceras_gerente):
        respuesta = cliente.post(
            "/api/carga",
            data={"proceso": "cambios"},
            headers=cabeceras_gerente,
            content_type="multipart/form-data",
        )
        assert respuesta.status_code == 403

    def test_proceso_invalido(self, cliente, cabeceras_analista):
        respuesta = cliente.post(
            "/api/carga",
            data={"proceso": "inexistente"},
            headers=cabeceras_analista,
            content_type="multipart/form-data",
        )
        assert respuesta.status_code == 400

    def test_sin_archivo(self, cliente, cabeceras_analista):
        respuesta = cliente.post(
            "/api/carga",
            data={"proceso": "cambios"},
            headers=cabeceras_analista,
            content_type="multipart/form-data",
        )
        assert respuesta.status_code == 400

    def test_formato_no_admitido(self, cliente, cabeceras_analista):
        import io

        respuesta = cliente.post(
            "/api/carga",
            data={
                "proceso": "cambios",
                "archivo": (io.BytesIO(b"contenido"), "datos.txt"),
            },
            headers=cabeceras_analista,
            content_type="multipart/form-data",
        )
        assert respuesta.status_code == 400


# ==================================================================
# Incidencias (RF8)
# ==================================================================
class TestIncidencias:
    def test_registro_valido(self, cliente, cabeceras_analista):
        respuesta = cliente.post(
            "/api/incidencias",
            json={
                "modulo": "Dashboard",
                "severidad": "Media",
                "titulo": "El grafico no carga",
                "descripcion": "Al abrir la evolucion de un indicador queda en blanco.",
            },
            headers=cabeceras_analista,
        )

        assert respuesta.status_code == 201
        assert respuesta.get_json()["estado"] == "Abierta"

    @pytest.mark.parametrize(
        "datos",
        [
            {"titulo": "ab", "descripcion": "descripcion suficientemente larga"},
            {"titulo": "Titulo valido", "descripcion": "corta"},
            {"titulo": "Titulo valido", "descripcion": "descripcion larga", "modulo": "Inventado"},
        ],
    )
    def test_solicitudes_incompletas(self, cliente, cabeceras_analista, datos):
        respuesta = cliente.post("/api/incidencias", json=datos, headers=cabeceras_analista)
        assert respuesta.status_code == 400

    def test_cualquier_perfil_puede_reportar(self, cliente, cabeceras_gerente):
        respuesta = cliente.post(
            "/api/incidencias",
            json={
                "titulo": "Observacion del gerente",
                "descripcion": "Descripcion con el detalle suficiente.",
            },
            headers=cabeceras_gerente,
        )
        assert respuesta.status_code == 201


# ==================================================================
# Exportación (RF6)
# ==================================================================
class TestExportacion:
    def test_csv(self, cliente, cabeceras_gerente):
        respuesta = cliente.get("/api/exportar?proceso=cambios", headers=cabeceras_gerente)

        assert respuesta.status_code == 200
        assert "text/csv" in respuesta.headers["Content-Type"]
        assert "Proceso;KPI" in respuesta.get_data(as_text=True)

    def test_reporte_html(self, cliente, cabeceras_gerente):
        respuesta = cliente.get("/api/reporte?proceso=cambios", headers=cabeceras_gerente)

        assert respuesta.status_code == 200
        assert "text/html" in respuesta.headers["Content-Type"]

    def test_reporte_pdf(self, cliente, cabeceras_gerente):
        pytest.importorskip("reportlab")

        respuesta = cliente.get("/api/reporte.pdf?proceso=cambios", headers=cabeceras_gerente)

        assert respuesta.status_code == 200
        assert respuesta.headers["Content-Type"] == "application/pdf"
        assert respuesta.get_data()[:4] == b"%PDF"
        assert "attachment" in respuesta.headers["Content-Disposition"]


# ==================================================================
# Conectores
# ==================================================================
class TestConectores:
    def test_informa_el_estado_de_cada_fuente(self, cliente, cabeceras_gerente):
        conectores = cliente.get("/api/conectores", headers=cabeceras_gerente).get_json()

        assert isinstance(conectores, list)
        assert all({"clave", "nombre", "conectado"} <= set(c) for c in conectores)

    def test_periodo_invalido_en_la_sincronizacion(self, cliente, cabeceras_analista):
        respuesta = cliente.post(
            "/api/sincronizar",
            json={"proceso": "cambios", "periodo": "marzo"},
            headers=cabeceras_analista,
        )
        assert respuesta.status_code == 400

    def test_el_gerente_no_sincroniza(self, cliente, cabeceras_gerente):
        respuesta = cliente.post(
            "/api/sincronizar",
            json={"proceso": "cambios", "periodo": "2025-03"},
            headers=cabeceras_gerente,
        )
        assert respuesta.status_code == 403


# ==================================================================
# Manejo de rutas inexistentes
# ==================================================================
class TestRutasInexistentes:
    def test_una_ruta_de_api_devuelve_json(self, cliente, cabeceras_gerente):
        respuesta = cliente.get("/api/inexistente", headers=cabeceras_gerente)

        assert respuesta.status_code == 404
        assert respuesta.get_json()["error"]
