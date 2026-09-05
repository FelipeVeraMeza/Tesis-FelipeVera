"""
Pruebas de autenticación y control de acceso.

Verifican el cumplimiento del requisito RNF3: cifrado de las credenciales y
acceso diferenciado por perfil. Son las pruebas de mayor criticidad, ya que un
fallo aquí comprometería la confidencialidad de la información.
"""
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import auth  # noqa: E402


# ==================================================================
# Cifrado de contraseñas (RNF3)
# ==================================================================
class TestCifradoDeContrasenas:
    def test_la_contrasena_no_se_almacena_en_texto_plano(self):
        cifrada = auth.cifrar_contrasena("MiClave123")

        assert "MiClave123" not in cifrada
        assert cifrada.startswith("pbkdf2:sha256")

    def test_dos_cifrados_de_la_misma_clave_difieren(self):
        """El uso de sal impide reconocer contraseñas repetidas."""
        primera = auth.cifrar_contrasena("MiClave123")
        segunda = auth.cifrar_contrasena("MiClave123")

        assert primera != segunda

    def test_la_verificacion_reconoce_la_clave_correcta(self):
        from werkzeug.security import check_password_hash

        cifrada = auth.cifrar_contrasena("MiClave123")

        assert check_password_hash(cifrada, "MiClave123")
        assert not check_password_hash(cifrada, "OtraClave")


# ==================================================================
# Tokens de sesión
# ==================================================================
class TestTokens:
    USUARIO = {
        "id_usuario": 1,
        "correo": "gerente@horizonte.cl",
        "nombre_usuario": "Gerente de TI",
        "rol": "Gerente",
    }

    def test_un_token_valido_se_reconoce(self):
        datos = auth.validar_token(auth.generar_token(self.USUARIO))

        assert datos is not None
        assert datos["correo"] == "gerente@horizonte.cl"
        assert datos["rol"] == "Gerente"

    def test_un_token_alterado_se_rechaza(self):
        """La firma impide modificar el contenido del token."""
        token = auth.generar_token(self.USUARIO)
        alterado = token[:-6] + "AAAAAA"

        assert auth.validar_token(alterado) is None

    def test_un_token_sin_firma_se_rechaza(self):
        token = auth.generar_token(self.USUARIO)
        solo_contenido = token.split(".")[0]

        assert auth.validar_token(solo_contenido) is None

    def test_un_token_expirado_se_rechaza(self, monkeypatch):
        """Una sesión vencida deja de ser válida."""
        token = auth.generar_token(self.USUARIO)

        # Se simula el paso del tiempo más allá de la duración de la sesión.
        # El instante actual se captura antes de sustituir la función, para
        # no invocarla de forma recursiva.
        futuro = time.time() + auth.DURACION_SESION + 60
        monkeypatch.setattr(auth.time, "time", lambda: futuro)

        assert auth.validar_token(token) is None

    @pytest.mark.parametrize("entrada", ["", "cualquier-cosa", "a.b", "..", "x" * 500])
    def test_entradas_invalidas_no_producen_errores(self, entrada):
        """Un token mal formado se rechaza sin interrumpir el sistema."""
        assert auth.validar_token(entrada) is None

    def test_un_token_de_otro_usuario_conserva_su_identidad(self):
        analista = dict(self.USUARIO, id_usuario=3, rol="Analista")
        datos = auth.validar_token(auth.generar_token(analista))

        assert datos["rol"] == "Analista"
        assert datos["id_usuario"] == 3


# ==================================================================
# Atribuciones de cada perfil (RF4, RF5)
# ==================================================================
class TestPermisos:
    """
    Las atribuciones corresponden a los usuarios definidos en el alcance:
    gerencia, líderes de proceso, analistas y administrador del sistema.
    """

    def test_estan_definidos_los_cuatro_perfiles(self):
        assert set(auth.PERMISOS) == {"Gerente", "Lider", "Analista", "Administrador"}

    def test_la_gerencia_no_carga_archivos(self):
        """La carga de datos corresponde a los analistas de proceso."""
        assert auth.PERMISOS["Gerente"]["puede_cargar"] is False
        assert auth.PERMISOS["Lider"]["puede_cargar"] is False

    def test_el_analista_carga_archivos(self):
        assert auth.PERMISOS["Analista"]["puede_cargar"] is True
        assert auth.PERMISOS["Administrador"]["puede_cargar"] is True

    def test_el_analista_no_emite_alertas(self):
        """Notificar al responsable compete a la gerencia y a los líderes."""
        assert auth.PERMISOS["Analista"]["puede_notificar"] is False

    def test_la_gerencia_y_los_lideres_emiten_alertas(self):
        assert auth.PERMISOS["Gerente"]["puede_notificar"] is True
        assert auth.PERMISOS["Lider"]["puede_notificar"] is True

    def test_todos_los_perfiles_exportan_resultados(self):
        assert all(p["puede_exportar"] for p in auth.PERMISOS.values())

    def test_cada_perfil_tiene_su_propia_vista(self):
        vistas = {rol: p["vista"] for rol, p in auth.PERMISOS.items()}

        assert vistas["Gerente"] == "ejecutiva"
        assert vistas["Lider"] == "consolidada"
        assert vistas["Analista"] == "detallada"
        assert vistas["Administrador"] == "administracion"

    def test_todos_los_perfiles_declaran_las_mismas_atribuciones(self):
        """Ningún perfil debe quedar con una atribución sin definir."""
        esperadas = {
            "vista",
            "puede_cargar",
            "puede_notificar",
            "puede_exportar",
            "ve_todos",
        }
        for rol, permisos in auth.PERMISOS.items():
            assert set(permisos) == esperadas, f"El perfil {rol} está incompleto"
