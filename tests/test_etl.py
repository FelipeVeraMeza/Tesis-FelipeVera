"""
Pruebas del proceso ETL.

Verifican las fórmulas de cálculo documentadas en las fichas técnicas y las
validaciones de integridad que se aplican a los archivos cargados. Un error
aquí produciría indicadores incorrectos sin que el usuario lo advierta.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import etl  # noqa: E402

ENCABEZADO_CAMBIOS = (
    "periodo,cambios_solicitados,cambios_aceptados,cambios_urgentes,"
    "cambios_implementados,cambios_revertidos,cambios_error_certificacion"
)


# ==================================================================
# Fórmulas de cálculo
# ==================================================================
class TestFormulasCambios:
    """Fórmulas del proceso de Gestión de Cambios."""

    FILA = {
        "periodo": "2025-03",
        "cambios_solicitados": 100,
        "cambios_aceptados": 90,
        "cambios_urgentes": 20,
        "cambios_implementados": 80,
        "cambios_revertidos": 4,
        "cambios_error_certificacion": 8,
    }

    def test_tasa_de_aceptacion(self):
        """(Aceptados / Solicitados) × 100"""
        assert etl.CALCULADORAS["cambios"](self.FILA)["cam_tasa_aceptacion"] == 90.0

    def test_porcentaje_de_urgentes(self):
        """(Urgentes / Solicitados) × 100"""
        assert etl.CALCULADORAS["cambios"](self.FILA)["cam_urgentes"] == 20.0

    def test_vuelta_atras_se_calcula_sobre_implementados(self):
        """(Revertidos / Implementados) × 100 — no sobre los solicitados."""
        assert etl.CALCULADORAS["cambios"](self.FILA)["cam_vuelta_atras"] == 5.0

    def test_error_en_certificacion(self):
        """(Con error / Implementados) × 100"""
        assert etl.CALCULADORAS["cambios"](self.FILA)["cam_error_certificacion"] == 10.0


class TestFormulasIncidentes:
    FILA = {
        "periodo": "2025-03",
        "incidentes_creados": 200,
        "incidentes_cerrados": 180,
        "horas_totales_resolucion": 900,
    }

    def test_tiempo_medio_de_resolucion(self):
        """Horas totales / Incidentes cerrados"""
        assert etl.CALCULADORAS["incidentes"](self.FILA)["inc_tiempo_resolucion"] == 5.0

    def test_capacidad_de_cierre(self):
        """(Cerrados / Creados) × 100"""
        assert etl.CALCULADORAS["incidentes"](self.FILA)["inc_capacidad_cierre"] == 90.0


class TestFormulasRequerimientos:
    FILA = {
        "periodo": "2025-03",
        "requerimientos_cerrados": 200,
        "requerimientos_rechazados": 15,
        "dias_totales_resolucion": 800,
        "requerimientos_dentro_sla": 170,
    }

    def test_rechazados_es_una_sumatoria(self):
        """Este indicador no es un porcentaje, sino un conteo."""
        assert etl.CALCULADORAS["requerimientos"](self.FILA)["req_rechazados"] == 15

    def test_tiempo_medio_de_resolucion(self):
        assert etl.CALCULADORAS["requerimientos"](self.FILA)["req_tiempo_medio"] == 4.0

    def test_cumplimiento_de_sla(self):
        assert etl.CALCULADORAS["requerimientos"](self.FILA)["req_sla"] == 85.0


class TestFormulasDemanda:
    FILA = {
        "periodo": "2025-03",
        "solicitudes_totales": 50,
        "dias_totales_evaluacion": 600,
        "solicitudes_dentro_sla": 45,
    }

    def test_tiempo_de_ciclo(self):
        assert etl.CALCULADORAS["demanda"](self.FILA)["dem_tiempo_ciclo"] == 12.0

    def test_evaluadas_dentro_de_sla(self):
        assert etl.CALCULADORAS["demanda"](self.FILA)["dem_sla_evaluacion"] == 90.0


class TestDivisionPorCero:
    """Un período sin actividad no debe interrumpir el procesamiento."""

    def test_periodo_sin_movimiento(self):
        resultado = etl.CALCULADORAS["cambios"](
            {
                "periodo": "2025-03",
                "cambios_solicitados": 0,
                "cambios_aceptados": 0,
                "cambios_urgentes": 0,
                "cambios_implementados": 0,
                "cambios_revertidos": 0,
                "cambios_error_certificacion": 0,
            }
        )
        # Los indicadores quedan sin valor, en lugar de producir un error
        assert all(valor is None for valor in resultado.values())


# ==================================================================
# Validación de los archivos (RF2)
# ==================================================================
class TestValidacion:
    def test_archivo_correcto(self):
        contenido = f"{ENCABEZADO_CAMBIOS}\n2025-01,100,90,20,80,4,8\n"
        filas, advertencias = etl.validar_y_leer(contenido, "cambios")

        assert len(filas) == 1
        assert advertencias == []
        assert filas[0]["periodo"] == "2025-01"

    def test_faltan_columnas_obligatorias(self):
        with pytest.raises(etl.ErrorETL, match="Faltan columnas"):
            etl.validar_y_leer("periodo,cambios_solicitados\n2025-01,100\n", "cambios")

    def test_archivo_vacio(self):
        with pytest.raises(etl.ErrorETL):
            etl.validar_y_leer("", "cambios")

    def test_proceso_no_reconocido(self):
        with pytest.raises(etl.ErrorETL, match="Proceso no reconocido"):
            etl.validar_y_leer(f"{ENCABEZADO_CAMBIOS}\n", "inexistente")

    @pytest.mark.parametrize("periodo", ["2025-13", "2025-00", "marzo", "2025/03", ""])
    def test_periodos_invalidos_se_omiten(self, periodo):
        """Una fila con período inválido se descarta e informa."""
        contenido = (
            f"{ENCABEZADO_CAMBIOS}\n"
            f"{periodo},100,90,20,80,4,8\n"
            "2025-02,100,90,20,80,4,8\n"
        )
        filas, advertencias = etl.validar_y_leer(contenido, "cambios")

        assert len(filas) == 1
        assert filas[0]["periodo"] == "2025-02"
        assert any("periodo" in a for a in advertencias)

    def test_valor_no_numerico(self):
        contenido = (
            f"{ENCABEZADO_CAMBIOS}\n"
            "2025-01,100,abc,20,80,4,8\n"
            "2025-02,100,90,20,80,4,8\n"
        )
        filas, advertencias = etl.validar_y_leer(contenido, "cambios")

        assert len(filas) == 1
        assert any("numerico" in a for a in advertencias)

    def test_valor_negativo(self):
        contenido = (
            f"{ENCABEZADO_CAMBIOS}\n"
            "2025-01,100,-5,20,80,4,8\n"
            "2025-02,100,90,20,80,4,8\n"
        )
        filas, advertencias = etl.validar_y_leer(contenido, "cambios")

        assert len(filas) == 1
        assert any("negativo" in a for a in advertencias)

    def test_periodo_duplicado_en_el_archivo(self):
        contenido = (
            f"{ENCABEZADO_CAMBIOS}\n"
            "2025-01,100,90,20,80,4,8\n"
            "2025-01,200,180,40,160,8,16\n"
        )
        filas, advertencias = etl.validar_y_leer(contenido, "cambios")

        assert len(filas) == 1
        assert any("duplicado" in a for a in advertencias)

    def test_incoherencia_entre_subconjunto_y_total(self):
        """
        Aceptar más cambios de los solicitados es imposible: la fila se
        procesa, pero se deja constancia de la inconsistencia.
        """
        contenido = f"{ENCABEZADO_CAMBIOS}\n2025-01,100,120,20,80,4,8\n"
        filas, advertencias = etl.validar_y_leer(contenido, "cambios")

        assert len(filas) == 1
        assert any("supera" in a for a in advertencias)

    def test_ninguna_fila_valida(self):
        contenido = f"{ENCABEZADO_CAMBIOS}\n2025-99,100,90,20,80,4,8\n"
        with pytest.raises(etl.ErrorETL, match="Ninguna fila"):
            etl.validar_y_leer(contenido, "cambios")

    def test_admite_coma_decimal(self):
        """Excel en configuración regional española usa coma decimal."""
        contenido = f"{ENCABEZADO_CAMBIOS}\n2025-01,100,90,20,80,4,5\n"
        filas, _ = etl.validar_y_leer(contenido, "cambios")
        assert filas[0]["cambios_error_certificacion"] == 5.0

    def test_ignora_el_marcador_de_orden_de_bytes(self):
        """Excel antepone un BOM al guardar en UTF-8."""
        contenido = f"﻿{ENCABEZADO_CAMBIOS}\n2025-01,100,90,20,80,4,8\n"
        filas, _ = etl.validar_y_leer(contenido, "cambios")
        assert len(filas) == 1


# ==================================================================
# Conversión de planillas de cálculo (RF1)
# ==================================================================
class TestConversionExcel:
    def test_una_planilla_produce_el_mismo_csv(self):
        openpyxl = pytest.importorskip("openpyxl")

        libro = openpyxl.Workbook()
        hoja = libro.active
        hoja.append(ENCABEZADO_CAMBIOS.split(","))
        hoja.append(["2025-01", 100, 90, 20, 80, 4, 8])

        import io

        memoria = io.BytesIO()
        libro.save(memoria)

        convertido = etl.convertir_excel(memoria.getvalue())
        filas, advertencias = etl.validar_y_leer(convertido, "cambios")

        assert len(filas) == 1
        assert advertencias == []
        assert filas[0]["cambios_solicitados"] == 100

    def test_planilla_sin_datos(self):
        openpyxl = pytest.importorskip("openpyxl")

        libro = openpyxl.Workbook()
        libro.active.append(ENCABEZADO_CAMBIOS.split(","))

        import io

        memoria = io.BytesIO()
        libro.save(memoria)

        with pytest.raises(etl.ErrorETL, match="no contiene datos"):
            etl.convertir_excel(memoria.getvalue())

    def test_archivo_que_no_es_una_planilla(self):
        with pytest.raises(etl.ErrorETL, match="No se pudo leer"):
            etl.convertir_excel(b"esto no es un archivo de Excel")


# ==================================================================
# Limpieza y normalización (pandas / NumPy)
# ==================================================================
class TestNormalizacion:
    """
    La normalización ordena la serie y detecta valores fuera de lo habitual,
    sin descartarlos: pueden corresponder a situaciones operativas reales.
    """

    @staticmethod
    def _serie(valores):
        return [
            {
                "periodo": periodo,
                "cambios_solicitados": valor,
                "cambios_aceptados": 90,
                "cambios_urgentes": 10,
                "cambios_implementados": 88,
                "cambios_revertidos": 2,
                "cambios_error_certificacion": 3,
            }
            for periodo, valor in valores
        ]

    def test_ordena_la_serie_cronologicamente(self):
        """El archivo puede venir desordenado; la serie no debe quedarlo."""
        desordenada = self._serie(
            [("2025-03", 100), ("2025-01", 100), ("2025-02", 100)]
        )
        normalizada, _ = etl.normalizar_datos(desordenada, "cambios")

        assert [f["periodo"] for f in normalizada] == ["2025-01", "2025-02", "2025-03"]

    def test_detecta_un_valor_atipico(self):
        serie = self._serie(
            [
                ("2025-01", 100),
                ("2025-02", 105),
                ("2025-03", 98),
                ("2025-04", 102),
                ("2025-05", 900),
            ]
        )
        _, advertencias = etl.normalizar_datos(serie, "cambios")

        assert len(advertencias) == 1
        assert "2025-05" in advertencias[0]
        assert "atipico" in advertencias[0]

    def test_el_valor_atipico_se_conserva(self):
        """Se advierte, pero el dato se registra igualmente."""
        serie = self._serie(
            [
                ("2025-01", 100),
                ("2025-02", 105),
                ("2025-03", 98),
                ("2025-04", 102),
                ("2025-05", 900),
            ]
        )
        normalizada, _ = etl.normalizar_datos(serie, "cambios")

        assert len(normalizada) == 5
        assert normalizada[-1]["cambios_solicitados"] == 900

    def test_una_serie_estable_no_genera_advertencias(self):
        serie = self._serie(
            [
                ("2025-01", 100),
                ("2025-02", 105),
                ("2025-03", 98),
                ("2025-04", 102),
                ("2025-05", 101),
            ]
        )
        _, advertencias = etl.normalizar_datos(serie, "cambios")

        assert advertencias == []

    def test_serie_demasiado_corta(self):
        """Con pocos períodos no hay base para juzgar qué es atípico."""
        serie = self._serie([("2025-01", 100), ("2025-02", 900)])
        _, advertencias = etl.normalizar_datos(serie, "cambios")

        assert advertencias == []

    def test_serie_vacia(self):
        normalizada, advertencias = etl.normalizar_datos([], "cambios")

        assert normalizada == []
        assert advertencias == []
