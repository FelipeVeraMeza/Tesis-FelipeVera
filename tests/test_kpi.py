"""
Pruebas de la lógica de evaluación de indicadores.

Verifican la clasificación del desempeño, el cálculo del cumplimiento y el
análisis de tendencias, que son el núcleo del sistema: de ellos dependen los
semáforos del panel, las alertas y las proyecciones.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.kpi import (  # noqa: E402
    analizar_tendencia,
    evaluar_estado,
    holgura,
    porcentaje_cumplimiento,
    proyectar,
)

ASCENDENTE = 1
DESCENDENTE = 2


# ==================================================================
# Clasificación del desempeño
# ==================================================================
class TestEvaluarEstado:
    """Un indicador se clasifica según su tendencia esperada."""

    @pytest.mark.parametrize(
        "valor, esperado",
        [
            (95, "cumple"),   # sobre la meta
            (90, "cumple"),   # exactamente en la meta
            (85, "riesgo"),   # dentro del margen de tolerancia
            (72, "riesgo"),   # en el límite del margen (80 % de la meta)
            (60, "bajo"),     # bajo el margen
        ],
    )
    def test_indicador_ascendente(self, valor, esperado):
        """Con meta 90 y tendencia ascendente, mayor valor es mejor."""
        assert evaluar_estado(valor, 90, ASCENDENTE) == esperado

    @pytest.mark.parametrize(
        "valor, esperado",
        [
            (3, "cumple"),    # bajo la meta
            (5, "cumple"),    # exactamente en la meta
            (5.5, "riesgo"),  # levemente por encima
            (6, "riesgo"),    # en el límite del margen (120 % de la meta)
            (9, "bajo"),      # muy por encima
        ],
    )
    def test_indicador_descendente(self, valor, esperado):
        """Con meta 5 y tendencia descendente, menor valor es mejor."""
        assert evaluar_estado(valor, 5, DESCENDENTE) == esperado

    def test_sin_medicion(self):
        """Un indicador sin valor no se clasifica como incumplimiento."""
        assert evaluar_estado(None, 90, ASCENDENTE) == "sin_datos"

    def test_sin_meta(self):
        """Sin meta definida no hay contra qué comparar."""
        assert evaluar_estado(95, None, ASCENDENTE) == "sin_datos"


# ==================================================================
# Porcentaje de cumplimiento
# ==================================================================
class TestPorcentajeCumplimiento:
    """El cumplimiento alimenta el promedio por proceso del panel."""

    def test_alcanzar_la_meta_es_cumplimiento_pleno(self):
        assert porcentaje_cumplimiento(90, 90, ASCENDENTE) == 100.0

    def test_superar_la_meta_no_excede_el_cien_por_ciento(self):
        """Superar la meta no debe inflar el promedio del proceso."""
        assert porcentaje_cumplimiento(150, 90, ASCENDENTE) == 100.0

    def test_meta_descendente_alcanzada(self):
        assert porcentaje_cumplimiento(4, 5, DESCENDENTE) == 100.0

    def test_meta_descendente_incumplida(self):
        """Con meta 5 y valor 10, el cumplimiento es del 50 %."""
        assert porcentaje_cumplimiento(10, 5, DESCENDENTE) == 50.0

    def test_cumplimiento_parcial(self):
        assert porcentaje_cumplimiento(45, 90, ASCENDENTE) == 50.0

    def test_sin_datos_devuelve_none(self):
        """Devolver None permite excluir el indicador del promedio."""
        assert porcentaje_cumplimiento(None, 90, ASCENDENTE) is None
        assert porcentaje_cumplimiento(50, None, ASCENDENTE) is None

    def test_meta_negativa(self):
        """
        Las metas negativas expresan un límite tolerado: mantenerse dentro
        de esa magnitud constituye cumplimiento pleno, y excederla reduce
        el resultado en proporción.
        """
        assert porcentaje_cumplimiento(-3, -5, ASCENDENTE) == 100.0
        assert porcentaje_cumplimiento(-10, -5, ASCENDENTE) == 50.0

    def test_meta_cero(self):
        """Con meta cero el cumplimiento se resuelve por el estado."""
        assert porcentaje_cumplimiento(0, 0, DESCENDENTE) == 100.0


# ==================================================================
# Proyección de tendencias
# ==================================================================
class TestProyectar:
    """La proyección estima el período siguiente (RF10)."""

    def test_serie_creciente(self):
        """Una serie que sube uno por período proyecta el siguiente valor."""
        assert proyectar([10, 11, 12, 13, 14]) == pytest.approx(15.0)

    def test_serie_decreciente(self):
        assert proyectar([20, 18, 16, 14]) == pytest.approx(12.0)

    def test_serie_constante(self):
        assert proyectar([50, 50, 50, 50]) == pytest.approx(50.0)

    def test_serie_insuficiente(self):
        """Con menos de tres puntos no hay tendencia que estimar."""
        assert proyectar([10, 20]) is None
        assert proyectar([]) is None

    def test_se_respeta_el_limite_inferior(self):
        """Un porcentaje no puede proyectarse por debajo de cero."""
        resultado = proyectar([5, 3, 1, 0], limite_inferior=0)
        assert resultado >= 0

    def test_se_respeta_el_limite_superior(self):
        resultado = proyectar([90, 95, 99, 100], limite_superior=100)
        assert resultado <= 100


# ==================================================================
# Análisis estadístico de la serie
# ==================================================================
class TestAnalizarTendencia:
    """El análisis informa cuánta confianza merece la proyección."""

    def test_serie_perfectamente_lineal(self):
        """Un ajuste perfecto corresponde a un R² igual a 1."""
        analisis = analizar_tendencia([10, 12, 14, 16, 18])

        assert analisis["r2"] == pytest.approx(1.0)
        assert analisis["confiabilidad"] == "alta"
        assert analisis["direccion"] == "ascendente"
        assert analisis["pendiente"] == pytest.approx(2.0)

    def test_serie_erratica_tiene_baja_confiabilidad(self):
        analisis = analizar_tendencia([10, 90, 20, 85, 15, 95])
        assert analisis["confiabilidad"] == "baja"

    def test_serie_estable(self):
        """Una variación marginal se informa como estable."""
        analisis = analizar_tendencia([50, 50.1, 49.9, 50, 50.05])
        assert analisis["direccion"] == "estable"

    def test_serie_descendente(self):
        analisis = analizar_tendencia([30, 25, 20, 15, 10])
        assert analisis["direccion"] == "descendente"
        assert analisis["pendiente"] < 0

    def test_serie_insuficiente(self):
        assert analizar_tendencia([10, 20]) is None

    def test_informa_la_cantidad_de_periodos(self):
        analisis = analizar_tendencia([1, 2, 3, 4, 5, 6, 7])
        assert analisis["periodos"] == 7

    def test_volatilidad_refleja_la_dispersion(self):
        """Una serie constante no presenta dispersión."""
        estable = analizar_tendencia([50, 50, 50, 50])
        variable = analizar_tendencia([10, 90, 20, 80])

        assert estable["volatilidad"] == 0
        assert variable["volatilidad"] > estable["volatilidad"]


# ==================================================================
# Caso real tomado del levantamiento
# ==================================================================
class TestCasoReal:
    """
    Serie efectiva del indicador "Porcentaje de cambios urgentes",
    medida entre septiembre de 2024 y marzo de 2025.
    """

    SERIE = [28.83, 28.24, 26.0, 25.05, 4.69, 8.91, 6.83]
    META = 30.0

    def test_el_indicador_cumple_su_meta(self):
        assert evaluar_estado(self.SERIE[-1], self.META, DESCENDENTE) == "cumple"

    def test_la_tendencia_es_descendente(self):
        analisis = analizar_tendencia(self.SERIE, limite_inferior=0, limite_superior=100)
        assert analisis["direccion"] == "descendente"

    def test_el_ajuste_es_confiable(self):
        """Un R² sobre 0,7 respalda que la mejora es sostenida."""
        analisis = analizar_tendencia(self.SERIE, limite_inferior=0, limite_superior=100)
        assert analisis["r2"] > 0.7
        assert analisis["confiabilidad"] == "alta"

    def test_la_proyeccion_no_es_negativa(self):
        """Un porcentaje proyectado nunca puede ser menor que cero."""
        analisis = analizar_tendencia(self.SERIE, limite_inferior=0, limite_superior=100)
        assert analisis["proyeccion"] >= 0


# ==================================================================
# Metas expresadas como límite negativo
# ==================================================================
class TestMetasNegativas:
    """
    Algunos indicadores expresan su meta como una desviación máxima
    tolerada. En «Desviación de la cartera de proyectos», por ejemplo, la
    meta es −5 %: acercarse a cero representa un mejor desempeño, y
    alejarse, uno peor.
    """

    META = -5.0

    @pytest.mark.parametrize(
        "valor, esperado",
        [
            (-2, "cumple"),   # menor desviación que el límite
            (-3, "cumple"),   # dentro del límite
            (-5, "cumple"),   # exactamente en el límite
            (-6, "riesgo"),   # levemente por encima
            (-9, "bajo"),     # muy por encima
        ],
    )
    def test_clasificacion(self, valor, esperado):
        assert evaluar_estado(valor, self.META, ASCENDENTE) == esperado

    def test_dentro_del_limite_es_cumplimiento_pleno(self):
        assert porcentaje_cumplimiento(-3, self.META, ASCENDENTE) == 100.0

    def test_fuera_del_limite_reduce_el_cumplimiento(self):
        assert porcentaje_cumplimiento(-10, self.META, ASCENDENTE) == 50.0

    def test_la_holgura_es_positiva_dentro_del_limite(self):
        assert holgura(-3, self.META, ASCENDENTE) == 40.0

    def test_la_holgura_es_negativa_fuera_del_limite(self):
        assert holgura(-6, self.META, ASCENDENTE) == -20.0


# ==================================================================
# Margen respecto a la meta
# ==================================================================
class TestHolgura:
    """
    El cumplimiento se acota a 100 %, de modo que no distingue entre
    alcanzar la meta y superarla holgadamente. La holgura conserva esa
    distancia.
    """

    def test_meta_ascendente_superada(self):
        """Con meta 90 y valor 99, el margen es del 10 %."""
        assert holgura(99, 90, ASCENDENTE) == 10.0

    def test_meta_ascendente_incumplida(self):
        assert holgura(81, 90, ASCENDENTE) == -10.0

    def test_meta_descendente_superada(self):
        """Con meta 20 y valor 15, el margen es del 25 %."""
        assert holgura(15, 20, DESCENDENTE) == 25.0

    def test_meta_descendente_incumplida(self):
        assert holgura(25, 20, DESCENDENTE) == -25.0

    def test_exactamente_en_la_meta(self):
        assert holgura(90, 90, ASCENDENTE) == 0.0

    def test_sin_datos(self):
        assert holgura(None, 90, ASCENDENTE) is None
        assert holgura(50, None, ASCENDENTE) is None
        assert holgura(50, 0, ASCENDENTE) is None

    def test_distingue_lo_que_el_cumplimiento_iguala(self):
        """
        Dos indicadores que cumplen su meta con márgenes distintos
        comparten el mismo cumplimiento, pero no la misma holgura.
        """
        ajustado = porcentaje_cumplimiento(20, 20, DESCENDENTE)
        holgado = porcentaje_cumplimiento(10, 20, DESCENDENTE)

        assert ajustado == holgado == 100.0
        assert holgura(20, 20, DESCENDENTE) < holgura(10, 20, DESCENDENTE)
