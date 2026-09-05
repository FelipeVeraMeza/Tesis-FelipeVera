"""
Alertas y notificaciones de desempeño (RF7).

Cuando un indicador se clasifica como "En riesgo" o "Bajo desempeño", el
Gerente o el Líder de TI puede notificar al responsable del proceso desde la
misma interfaz de visualización.

En esta etapa de prototipo el envío es simulado: la notificación se registra en
la base de datos y se confirma en pantalla. La estructura del módulo contempla
la integración futura con un servidor de correo SMTP, que solo requeriría
implementar `_enviar_por_correo` sin alterar el resto del flujo.
"""
import re
import smtplib
import unicodedata
from email.message import EmailMessage
from html import escape

from . import config, db, kpi

# Texto que acompaña a cada estado en el mensaje de la notificación
DESCRIPCION_ESTADO = {
    "riesgo": "en riesgo de incumplimiento",
    "bajo": "con bajo desempeño",
}

DESTINATARIO_POR_DEFECTO = "Gerencia de Tecnologías de la Información"


class ErrorNotificacion(Exception):
    """No fue posible emitir la notificación."""


def _formatear(valor, unidad: str | None) -> str:
    if valor is None:
        return "sin dato"
    texto = f"{float(valor):g}"
    if unidad == "%":
        return f"{texto} %"
    if unidad in (None, "", "cantidad", "unidad"):
        return texto
    return f"{texto} {unidad}"


def componer_mensaje(indicador: dict, emisor: dict) -> tuple[str, str]:
    """Arma el asunto y el cuerpo de la notificación."""
    situacion = DESCRIPCION_ESTADO.get(indicador["estado"], "fuera de meta")

    asunto = f"Alerta de desempeño · {indicador['nombre']}"

    mensaje = (
        f"El indicador «{indicador['nombre']}» del proceso "
        f"{indicador['proceso_nombre']} se encuentra {situacion}.\n\n"
        f"Valor registrado: {_formatear(indicador['valor'], indicador['unidad'])}\n"
        f"Meta comprometida: {_formatear(indicador['meta'], indicador['unidad'])}\n"
        f"Tendencia esperada: {indicador['tendencia']}\n\n"
        f"Se solicita revisar las causas de la desviación y definir las acciones "
        f"correctivas correspondientes.\n\n"
        f"Notificación emitida por {emisor.get('nombre', 'el sistema')} "
        f"({emisor.get('rol', '—')})."
    )

    return asunto[:200], mensaje[:1000]


def _correo_destinatario(nombre_responsable: str) -> str:
    """
    Deriva la dirección institucional del responsable del proceso.

    En la organización las casillas siguen el formato nombre@dominio; ante un
    responsable sin correo registrado se utiliza la casilla de la Gerencia.
    """
    if not nombre_responsable:
        return config.CORREO_GERENCIA

    # Se toma el primer nombre, normalizado y sin acentos
    primero = nombre_responsable.strip().split("/")[0].split()[0].lower()
    limpio = unicodedata.normalize("NFKD", primero)
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    limpio = re.sub(r"[^a-z0-9]", "", limpio)

    return f"{limpio}@{config.DOMINIO_CORREO}" if limpio else config.CORREO_GERENCIA


def _cuerpo_html(indicador: dict, mensaje: str) -> str:
    """Versión en HTML del mensaje, para clientes de correo que la admitan."""
    color = "#d64545" if indicador["estado"] == "bajo" else "#d99411"
    parrafos = "".join(
        f"<p style='margin:0 0 12px'>{escape(linea)}</p>"
        for linea in mensaje.split("\n\n")
        if linea.strip()
    )

    return f"""<!DOCTYPE html>
<html lang="es"><body style="margin:0;padding:24px;background:#f4f7fa;
 font-family:'Segoe UI',Arial,sans-serif;font-size:14px;color:#1c2833">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden">
    <div style="padding:18px 24px;background:#0f4c75;color:#fff">
      <strong style="font-size:16px">AFP Horizonte</strong><br>
      <span style="font-size:12px;opacity:.85">Gerencia de Tecnologías de la Información</span>
    </div>
    <div style="padding:24px;border-left:4px solid {color}">
      <h2 style="margin:0 0 16px;font-size:16px;color:#082f49">Alerta de desempeño</h2>
      {parrafos}
    </div>
    <div style="padding:14px 24px;background:#f4f7fa;font-size:11px;color:#5c6b7a">
      Mensaje generado automáticamente por el Sistema de Seguimiento de KPIs.
    </div>
  </div>
</body></html>"""


def _enviar_por_correo(
    destinatario: str, asunto: str, mensaje: str, indicador: dict
) -> tuple[bool, str]:
    """
    Envía la notificación mediante un servidor SMTP.

    El envío se realiza solo si el servidor está configurado en el archivo de
    entorno. En caso contrario la notificación queda registrada como simulada,
    conforme a lo previsto para la etapa de prototipo.

    Devuelve si el envío se concretó y el detalle correspondiente.
    """
    if not config.SMTP_ACTIVO:
        return False, "Servidor de correo no configurado"

    correo = _correo_destinatario(destinatario)

    aviso = EmailMessage()
    aviso["From"] = config.SMTP_REMITENTE
    aviso["To"] = correo
    aviso["Subject"] = asunto
    aviso.set_content(mensaje)
    aviso.add_alternative(_cuerpo_html(indicador, mensaje), subtype="html")

    try:
        if config.SMTP_SSL:
            servidor = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PUERTO, timeout=20)
        else:
            servidor = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PUERTO, timeout=20)
            if config.SMTP_TLS:
                servidor.starttls()

        with servidor:
            if config.SMTP_USUARIO:
                servidor.login(config.SMTP_USUARIO, config.SMTP_CLAVE)
            servidor.send_message(aviso)

        return True, correo

    except (smtplib.SMTPException, OSError) as exc:
        # El fallo del correo no debe impedir el registro de la alerta
        return False, f"No se pudo enviar el correo: {exc}"


def emitir(id_kpi: int, emisor: dict) -> dict:
    """
    Registra una notificación para el indicador indicado.

    Solo se admiten indicadores que efectivamente presenten una desviación,
    de modo que la alerta siempre corresponda a una situación real.
    """
    indicadores = [k for k in kpi.obtener_kpis() if k["id_kpi"] == id_kpi]
    if not indicadores:
        raise ErrorNotificacion("El indicador solicitado no existe.")

    indicador = indicadores[0]

    if indicador["estado"] not in ("riesgo", "bajo"):
        raise ErrorNotificacion(
            "El indicador no presenta desviaciones respecto a su meta, "
            "por lo que no corresponde emitir una alerta."
        )

    destinatario = (
        indicador.get("dueno_proceso")
        or indicador.get("proceso_nombre")
        or DESTINATARIO_POR_DEFECTO
    )

    asunto, mensaje = componer_mensaje(indicador, emisor)
    enviado, detalle = _enviar_por_correo(destinatario, asunto, mensaje, indicador)

    registro = db.insertar(
        "notificacion",
        {
            "id_kpi": id_kpi,
            "id_usuario": emisor.get("id_usuario"),
            "estado_kpi": indicador["estado"],
            "valor_registrado": indicador["valor"],
            "meta_referencia": indicador["meta"],
            "destinatario": destinatario[:150],
            "asunto": asunto,
            "mensaje": mensaje,
            "canal": "Correo" if enviado else "Simulado",
            "estado_envio": "Enviada" if enviado else "Registrada",
        },
    )

    return {
        "id_notificacion": registro[0]["id_notificacion"] if registro else None,
        "kpi": indicador["nombre"],
        "proceso": indicador["proceso_nombre"],
        "destinatario": destinatario,
        "correo": detalle if enviado else _correo_destinatario(destinatario),
        "asunto": asunto,
        "mensaje": mensaje,
        "estado_kpi": indicador["estado"],
        "canal": "Correo" if enviado else "Simulado",
        "simulada": not enviado,
        "detalle_envio": detalle,
    }


def historial(limite: int = 50) -> list[dict]:
    """Notificaciones emitidas, de la más reciente a la más antigua."""
    filas = db.seleccionar(
        "notificacion",
        {
            "select": "id_notificacion,estado_kpi,valor_registrado,meta_referencia,"
            "destinatario,asunto,canal,estado_envio,fecha_envio,"
            "indicador_kpi(nombre_kpi),usuario(nombre_usuario)",
            "order": "fecha_envio.desc",
            "limit": str(limite),
        },
    )

    return [
        {
            "id_notificacion": f["id_notificacion"],
            "kpi": (f.get("indicador_kpi") or {}).get("nombre_kpi"),
            "emisor": (f.get("usuario") or {}).get("nombre_usuario"),
            "destinatario": f["destinatario"],
            "asunto": f["asunto"],
            "estado_kpi": f["estado_kpi"],
            "valor": f["valor_registrado"],
            "meta": f["meta_referencia"],
            "canal": f["canal"],
            "estado_envio": f["estado_envio"],
            "fecha": f["fecha_envio"],
        }
        for f in filas
    ]
