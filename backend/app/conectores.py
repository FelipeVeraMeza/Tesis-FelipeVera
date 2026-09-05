"""
Conectores a fuentes de datos externas.

El documento del proyecto plantea, como línea de evolución, el desarrollo de
conectores que extraigan los datos directamente desde las herramientas de mesa
de ayuda, reduciendo la dependencia de la carga manual de archivos.

Este módulo implementa esa capa: define una interfaz común y una
implementación para Jira, que es la fuente primaria de los procesos de Gestión
de Cambios, Incidentes y Requerimientos según el levantamiento realizado.

La extracción se apoya en la API REST de Jira y produce exactamente la misma
estructura de datos que genera la lectura de un archivo CSV, de modo que el
resto del proceso ETL opera sin distinguir el origen.
"""
import base64
from collections import defaultdict
from datetime import datetime

import requests

from . import config, etl


class ErrorConector(Exception):
    """No fue posible obtener los datos desde la fuente externa."""


# ------------------------------------------------------------------
# Interfaz comun
# ------------------------------------------------------------------
class Conector:
    """
    Contrato que debe cumplir toda fuente de datos externa.

    Definirlo de forma explicita permite incorporar nuevas herramientas
    (ServiceNow, Remedy u otras) sin alterar el resto del sistema, conforme al
    requisito de escalabilidad RNF4.
    """

    nombre = "generico"

    def disponible(self) -> bool:
        """Indica si la fuente esta configurada y accesible."""
        raise NotImplementedError

    def extraer(self, proceso: str, periodo: str) -> dict:
        """Devuelve los datos del periodo con el formato que espera el ETL."""
        raise NotImplementedError


# ------------------------------------------------------------------
# Jira
# ------------------------------------------------------------------
class ConectorJira(Conector):
    """
    Extraccion desde Jira mediante su API REST.

    Cada proceso se corresponde con un proyecto de Jira y sus indicadores se
    obtienen contando incidencias que cumplen determinadas condiciones,
    expresadas como consultas JQL.
    """

    nombre = "Jira"

    # Consultas por proceso. Los marcadores {proyecto} y {periodo} se
    # sustituyen al momento de la extraccion.
    CONSULTAS = {
        "cambios": {
            "cambios_solicitados": 'project = {proyecto} AND created >= "{desde}" AND created <= "{hasta}"',
            "cambios_aceptados": 'project = {proyecto} AND status changed to ("Aprobado", "Approved") DURING ("{desde}", "{hasta}")',
            "cambios_urgentes": 'project = {proyecto} AND priority in (Highest, High) AND created >= "{desde}" AND created <= "{hasta}"',
            "cambios_implementados": 'project = {proyecto} AND status in (Done, Implementado) AND resolved >= "{desde}" AND resolved <= "{hasta}"',
            "cambios_revertidos": 'project = {proyecto} AND labels in (rollback, "vuelta-atras") AND resolved >= "{desde}" AND resolved <= "{hasta}"',
            "cambios_error_certificacion": 'project = {proyecto} AND labels in ("error-certificacion", "no-certificado") AND resolved >= "{desde}" AND resolved <= "{hasta}"',
        },
        "incidentes": {
            "incidentes_creados": 'project = {proyecto} AND issuetype = Incident AND created >= "{desde}" AND created <= "{hasta}"',
            "incidentes_cerrados": 'project = {proyecto} AND issuetype = Incident AND resolved >= "{desde}" AND resolved <= "{hasta}"',
        },
        "requerimientos": {
            "requerimientos_cerrados": 'project = {proyecto} AND resolved >= "{desde}" AND resolved <= "{hasta}"',
            "requerimientos_rechazados": 'project = {proyecto} AND resolution in (Rejected, Rechazado) AND resolved >= "{desde}" AND resolved <= "{hasta}"',
        },
        "demanda": {
            "solicitudes_totales": 'project = {proyecto} AND created >= "{desde}" AND created <= "{hasta}"',
        },
    }

    def __init__(self) -> None:
        self.url = config.JIRA_URL
        self.usuario = config.JIRA_USUARIO
        self.token = config.JIRA_TOKEN
        self.proyectos = config.JIRA_PROYECTOS

    # -------------------------------------------------------------
    def disponible(self) -> bool:
        return bool(self.url and self.usuario and self.token)

    def _cabeceras(self) -> dict:
        credencial = base64.b64encode(
            f"{self.usuario}:{self.token}".encode()
        ).decode()
        return {
            "Authorization": f"Basic {credencial}",
            "Accept": "application/json",
        }

    def _contar(self, jql: str) -> int:
        """Cantidad de incidencias que satisfacen la consulta."""
        try:
            respuesta = requests.get(
                f"{self.url.rstrip('/')}/rest/api/3/search",
                headers=self._cabeceras(),
                params={"jql": jql, "maxResults": 0},
                timeout=45,
            )
        except requests.RequestException as exc:
            raise ErrorConector(f"No se pudo consultar Jira: {exc}") from exc

        if respuesta.status_code == 401:
            raise ErrorConector("Credenciales de Jira rechazadas.")
        if respuesta.status_code >= 400:
            raise ErrorConector(
                f"Jira respondio {respuesta.status_code}: {respuesta.text[:200]}"
            )

        return int(respuesta.json().get("total", 0))

    def verificar(self) -> dict:
        """Comprueba la conectividad y las credenciales."""
        if not self.disponible():
            return {
                "conectado": False,
                "detalle": "Jira no esta configurado en el archivo .env",
            }

        try:
            respuesta = requests.get(
                f"{self.url.rstrip('/')}/rest/api/3/myself",
                headers=self._cabeceras(),
                timeout=30,
            )
        except requests.RequestException as exc:
            return {"conectado": False, "detalle": str(exc)}

        if respuesta.status_code != 200:
            return {
                "conectado": False,
                "detalle": f"HTTP {respuesta.status_code}",
            }

        cuenta = respuesta.json()
        return {
            "conectado": True,
            "usuario": cuenta.get("displayName"),
            "url": self.url,
            "proyectos": self.proyectos,
        }

    # -------------------------------------------------------------
    @staticmethod
    def _limites(periodo: str) -> tuple[str, str]:
        """Primer y ultimo dia del periodo indicado, en formato AAAA-MM."""
        anio, mes = (int(p) for p in periodo.split("-"))
        desde = f"{anio:04d}-{mes:02d}-01"

        if mes == 12:
            siguiente = datetime(anio + 1, 1, 1)
        else:
            siguiente = datetime(anio, mes + 1, 1)
        ultimo_dia = (siguiente - datetime.resolution).day

        return desde, f"{anio:04d}-{mes:02d}-{ultimo_dia:02d}"

    def extraer(self, proceso: str, periodo: str) -> dict:
        """Obtiene desde Jira los datos del proceso para un periodo."""
        if not self.disponible():
            raise ErrorConector(
                "Jira no esta configurado. Defina JIRA_URL, JIRA_USUARIO y "
                "JIRA_TOKEN en el archivo .env"
            )

        if proceso not in self.CONSULTAS:
            raise ErrorConector(f"No hay consultas definidas para el proceso {proceso}")

        proyecto = self.proyectos.get(proceso)
        if not proyecto:
            raise ErrorConector(
                f"No se ha asociado un proyecto de Jira al proceso {proceso}"
            )

        desde, hasta = self._limites(periodo)

        datos = {"periodo": periodo}
        for campo, plantilla in self.CONSULTAS[proceso].items():
            jql = plantilla.format(proyecto=proyecto, desde=desde, hasta=hasta)
            datos[campo] = self._contar(jql)

        # Las columnas que Jira no entrega directamente se completan en cero,
        # dejando constancia de que requieren medicion complementaria
        for columna in etl.COLUMNAS_ESPERADAS[proceso][1:]:
            datos.setdefault(columna, 0)

        return datos


# ------------------------------------------------------------------
# Registro de conectores disponibles
# ------------------------------------------------------------------
CONECTORES: dict[str, Conector] = {
    "jira": ConectorJira(),
}


def obtener(nombre: str) -> Conector:
    conector = CONECTORES.get(nombre.lower())
    if conector is None:
        raise ErrorConector(
            f"Conector no reconocido: {nombre}. "
            f"Disponibles: {', '.join(CONECTORES)}"
        )
    return conector


def estado() -> list[dict]:
    """Situación de cada conector, para mostrarla en la interfaz."""
    resumen = []
    for clave, conector in CONECTORES.items():
        fila = {"clave": clave, "nombre": conector.nombre}
        fila.update(
            conector.verificar()
            if hasattr(conector, "verificar")
            else {"conectado": conector.disponible()}
        )
        resumen.append(fila)
    return resumen
