"""
Generación de reportes consolidados (RF6).

Produce un documento con el estado de los indicadores, su cumplimiento y las
desviaciones detectadas, en dos formatos:

- **PDF**, generado directamente por el sistema y descargable como archivo,
  conforme al formato que menciona el requisito RF6.
- **HTML**, para consulta en pantalla y con estilos de impresión.

Ambos comparten la misma estructura: síntesis, cumplimiento por proceso y
detalle de indicadores, con la trazabilidad de quién emitió el documento y
cuándo.
"""
import io
from datetime import datetime
from html import escape

ETIQUETAS_ESTADO = {
    "cumple": "Cumple",
    "riesgo": "En riesgo",
    "bajo": "Bajo desempeño",
    "sin_datos": "Sin datos",
}

NOMBRES_ALCANCE = {
    "general": "todos los procesos",
    "criticos": "procesos críticos",
}

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _formatear(valor, unidad: str | None) -> str:
    if valor is None:
        return "—"
    numero = float(valor)
    texto = f"{numero:g}" if numero == int(numero) else f"{numero:.2f}"
    if unidad == "%":
        return f"{texto} %"
    if unidad in (None, "", "cantidad", "unidad"):
        return texto
    return f"{texto} {unidad}"


def _fecha_larga() -> str:
    ahora = datetime.now()
    return f"{ahora.day} de {MESES[ahora.month - 1]} de {ahora.year}, {ahora:%H:%M}"


def _filas_indicadores(indicadores: list[dict]) -> str:
    if not indicadores:
        return (
            '<tr><td colspan="7" class="vacio">No hay indicadores para el '
            "alcance seleccionado.</td></tr>"
        )

    filas = []
    for k in indicadores:
        filas.append(
            f"""
            <tr>
              <td>
                <strong>{escape(k['nombre'] or '')}</strong>
                <span class="detalle">{escape(k.get('formula') or '')}</span>
              </td>
              <td>{escape(k.get('proceso_nombre') or '—')}</td>
              <td class="num">{_formatear(k['valor'], k['unidad'])}</td>
              <td class="num">{_formatear(k['meta'], k['unidad'])}</td>
              <td>{'Ascendente' if k['tendencia'] == 'ascendente' else 'Descendente'}</td>
              <td><span class="estado {k['estado']}">{ETIQUETAS_ESTADO.get(k['estado'], '—')}</span></td>
              <td class="num">
                {_formatear(k.get('proyeccion'), k['unidad'])}
                {f'<span class="ajuste">R²={k["analisis"]["r2"]}</span>' if k.get('analisis') else ''}
              </td>
            </tr>"""
        )
    return "".join(filas)


def _filas_resumen(resumen: list[dict]) -> str:
    filas = []
    for bloque in resumen:
        promedio = bloque["cumplimiento_promedio"]
        filas.append(
            f"""
            <tr>
              <td>{escape(bloque['nombre'] or '')}{' <span class="marca">crítico</span>' if bloque.get('critico') else ''}</td>
              <td class="num">{f"{promedio} %" if promedio is not None else '—'}</td>
              <td class="num">{bloque['kpis_medidos']} / {bloque['total_kpis']}</td>
              <td class="num">{bloque['en_alerta']}</td>
            </tr>"""
        )
    return "".join(filas)


def generar_html(
    indicadores: list[dict],
    resumen: list[dict],
    alcance: str,
    usuario: dict,
) -> str:
    """Compone el reporte completo."""
    # El resumen se acota al alcance solicitado
    if alcance == "criticos":
        resumen = [b for b in resumen if b.get("critico")]
    elif alcance not in ("general", "criticos"):
        resumen = [b for b in resumen if b["proceso"] == alcance]

    nombre_alcance = NOMBRES_ALCANCE.get(alcance, alcance)
    if alcance not in NOMBRES_ALCANCE and resumen:
        nombre_alcance = resumen[0]["nombre"]

    medidos = [k for k in indicadores if k["estado"] != "sin_datos"]
    desviados = [k for k in indicadores if k["estado"] in ("riesgo", "bajo")]

    periodos = sorted({p["periodo"] for k in indicadores for p in k["historico"]})
    rango = f"{periodos[0]} a {periodos[-1]}" if periodos else "sin mediciones"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Reporte de KPIs · AFP Horizonte</title>
<style>
  @page {{ size: A4 landscape; margin: 14mm; }}

  * {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    padding: 28px;
    font-family: "Inter", -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
    font-size: 11.5px;
    color: #1c2833;
    background: #fff;
  }}

  header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    padding-bottom: 14px;
    margin-bottom: 22px;
    border-bottom: 2px solid #0f4c75;
  }}

  h1 {{ margin: 0; font-size: 19px; color: #0f4c75; }}
  .subtitulo {{ margin: 4px 0 0; font-size: 12.5px; color: #5c6b7a; }}
  .meta-doc {{ text-align: right; font-size: 11px; color: #5c6b7a; line-height: 1.7; }}

  h2 {{
    margin: 26px 0 10px;
    font-size: 13.5px;
    color: #082f49;
  }}

  /* Indicadores de sintesis */
  .sintesis {{
    display: flex;
    gap: 12px;
    margin-bottom: 6px;
  }}

  .dato {{
    flex: 1;
    padding: 12px 14px;
    background: #f4f7fa;
    border: 1px solid #dfe6ec;
    border-radius: 8px;
  }}

  .dato .cifra {{ font-size: 22px; font-weight: 700; color: #0f4c75; }}
  .dato .rotulo {{ font-size: 10.5px; color: #5c6b7a; }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 8px;
  }}

  th {{
    padding: 8px 10px;
    text-align: left;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .04em;
    color: #5c6b7a;
    background: #e8f1f8;
    border-bottom: 1px solid #dfe6ec;
  }}

  td {{
    padding: 8px 10px;
    border-bottom: 1px solid #eef1f4;
    vertical-align: top;
  }}

  td.num {{ text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }}

  .detalle {{
    display: block;
    margin-top: 2px;
    font-size: 10px;
    color: #5c6b7a;
  }}

  .estado {{
    display: inline-block;
    padding: 2px 8px;
    font-size: 10px;
    border-radius: 20px;
    white-space: nowrap;
  }}

  .estado.cumple    {{ background: #e6f6ec; color: #1d6b3c; }}
  .estado.riesgo    {{ background: #fdf3e0; color: #8a5d05; }}
  .estado.bajo      {{ background: #fdeaea; color: #9c2b2b; }}
  .estado.sin_datos {{ background: #eef1f4; color: #5c6b7a; }}

  .marca {{
    display: inline-block;
    margin-left: 6px;
    padding: 1px 7px;
    font-size: 9.5px;
    background: #e8f1f8;
    color: #0f4c75;
    border-radius: 20px;
  }}

  .ajuste {{
    display: block;
    margin-top: 2px;
    font-size: 9.5px;
    font-weight: 400;
    color: #5c6b7a;
  }}

  .vacio {{ padding: 18px; text-align: center; color: #5c6b7a; }}

  footer {{
    margin-top: 26px;
    padding-top: 12px;
    font-size: 10px;
    color: #5c6b7a;
    border-top: 1px solid #dfe6ec;
  }}

  /* Barra de accion, visible solo en pantalla */
  .acciones {{
    position: fixed;
    top: 16px;
    right: 16px;
    display: flex;
    gap: 8px;
  }}

  .acciones button {{
    padding: 9px 16px;
    font-family: inherit;
    font-size: 12.5px;
    color: #fff;
    background: #0f4c75;
    border: none;
    border-radius: 8px;
    cursor: pointer;
  }}

  @media print {{
    body {{ padding: 0; }}
    .acciones {{ display: none; }}
    tr {{ break-inside: avoid; }}
    h2 {{ break-after: avoid; }}
  }}
</style>
</head>
<body>

<div class="acciones">
  <button onclick="window.print()">Guardar como PDF</button>
</div>

<header>
  <div>
    <h1>Reporte de indicadores de desempeño</h1>
    <p class="subtitulo">AFP Horizonte · Gerencia de Tecnologías de la Información</p>
  </div>
  <div class="meta-doc">
    Alcance: {escape(nombre_alcance)}<br>
    Períodos: {escape(rango)}<br>
    Emitido: {_fecha_larga()}<br>
    Por: {escape(usuario.get('nombre', '—'))} ({escape(usuario.get('rol', '—'))})
  </div>
</header>

<section class="sintesis">
  <div class="dato">
    <div class="cifra">{len(indicadores)}</div>
    <div class="rotulo">Indicadores en el alcance</div>
  </div>
  <div class="dato">
    <div class="cifra">{len(medidos)}</div>
    <div class="rotulo">Con medición registrada</div>
  </div>
  <div class="dato">
    <div class="cifra">{len(desviados)}</div>
    <div class="rotulo">Fuera de meta</div>
  </div>
  <div class="dato">
    <div class="cifra">{len(resumen)}</div>
    <div class="rotulo">Procesos considerados</div>
  </div>
</section>

<h2>Cumplimiento por proceso</h2>
<table>
  <thead>
    <tr>
      <th>Proceso</th>
      <th class="num">Cumplimiento</th>
      <th class="num">Medidos</th>
      <th class="num">Fuera de meta</th>
    </tr>
  </thead>
  <tbody>{_filas_resumen(resumen)}</tbody>
</table>

<h2>Detalle de indicadores</h2>
<table>
  <thead>
    <tr>
      <th>Indicador</th>
      <th>Proceso</th>
      <th class="num">Valor</th>
      <th class="num">Meta</th>
      <th>Tendencia</th>
      <th>Estado</th>
      <th class="num">Proyección</th>
    </tr>
  </thead>
  <tbody>{_filas_indicadores(indicadores)}</tbody>
</table>

<footer>
  Documento generado automáticamente por el Sistema de Seguimiento de KPIs.
  Las proyecciones corresponden a estimaciones estadísticas lineales sobre la
  serie histórica de cada indicador.
  Prototipo académico · Datos con fines de titulación.
</footer>

</body>
</html>"""


# ==================================================================
# Generación del documento PDF
#
# Además del reporte en HTML, el sistema produce un archivo PDF
# descargable, dando cumplimiento literal al requisito RF6, que
# menciona ese formato de forma explícita.
# ==================================================================

# Paleta institucional, equivalente a la de la interfaz web
_AZUL = (0.059, 0.298, 0.459)
_AZUL_SUAVE = (0.910, 0.945, 0.973)
_GRIS = (0.361, 0.420, 0.478)
_BORDE = (0.874, 0.902, 0.925)

_COLOR_ESTADO = {
    "cumple": (0.114, 0.420, 0.235),
    "riesgo": (0.541, 0.365, 0.020),
    "bajo": (0.612, 0.169, 0.169),
    "sin_datos": (0.361, 0.420, 0.478),
}


def _recortar(texto: str, largo: int) -> str:
    texto = str(texto or "")
    return texto if len(texto) <= largo else texto[: largo - 1] + "…"


def generar_pdf(
    indicadores: list[dict],
    resumen: list[dict],
    alcance: str,
    usuario: dict,
) -> bytes:
    """Compone el reporte en PDF y lo devuelve como bytes."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    # El resumen se acota al alcance solicitado
    if alcance == "criticos":
        resumen = [b for b in resumen if b.get("critico")]
    elif alcance not in ("general", "criticos"):
        resumen = [b for b in resumen if b["proceso"] == alcance]

    nombre_alcance = NOMBRES_ALCANCE.get(alcance, alcance)
    if alcance not in NOMBRES_ALCANCE and resumen:
        nombre_alcance = resumen[0]["nombre"]

    medidos = [k for k in indicadores if k["estado"] != "sin_datos"]
    desviados = [k for k in indicadores if k["estado"] in ("riesgo", "bajo")]

    periodos = sorted({p["periodo"] for k in indicadores for p in k["historico"]})
    rango = f"{periodos[0]} a {periodos[-1]}" if periodos else "sin mediciones"

    buffer = io.BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Reporte de KPIs · AFP Horizonte",
        author="Sistema de Seguimiento de KPIs",
    )

    base = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "titulo", parent=base["Heading1"], fontSize=15, leading=19,
        textColor=colors.Color(*_AZUL), spaceAfter=2,
    )
    subtitulo = ParagraphStyle(
        "subtitulo", parent=base["Normal"], fontSize=9,
        textColor=colors.Color(*_GRIS),
    )
    seccion = ParagraphStyle(
        "seccion", parent=base["Heading2"], fontSize=11, leading=14,
        textColor=colors.Color(*_AZUL), spaceBefore=10, spaceAfter=5,
    )
    ficha = ParagraphStyle(
        "ficha", parent=base["Normal"], fontSize=8, leading=11,
        alignment=TA_RIGHT, textColor=colors.Color(*_GRIS),
    )
    celda = ParagraphStyle("celda", parent=base["Normal"], fontSize=7.5, leading=9.5)
    celda_menor = ParagraphStyle(
        "celda_menor", parent=celda, fontSize=6.5, leading=8,
        textColor=colors.Color(*_GRIS),
    )

    elementos = []

    # ---------------- Encabezado ----------------
    encabezado = Table(
        [[
            [
                Paragraph("Reporte de indicadores de desempeño", titulo),
                Paragraph(
                    "AFP Horizonte · Gerencia de Tecnologías de la Información",
                    subtitulo,
                ),
            ],
            Paragraph(
                f"Alcance: {escape(nombre_alcance)}<br/>"
                f"Períodos: {escape(rango)}<br/>"
                f"Emitido: {_fecha_larga()}<br/>"
                f"Por: {escape(usuario.get('nombre', '—'))} "
                f"({escape(usuario.get('rol', '—'))})",
                ficha,
            ),
        ]],
        colWidths=[165 * mm, 104 * mm],
    )
    encabezado.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("LINEBELOW", (0, 0), (-1, -1), 1.2, colors.Color(*_AZUL)),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    elementos += [encabezado, Spacer(1, 10)]

    # ---------------- Síntesis ----------------
    sintesis = Table(
        [
            [str(len(indicadores)), str(len(medidos)), str(len(desviados)), str(len(resumen))],
            [
                "Indicadores en el alcance",
                "Con medición registrada",
                "Fuera de meta",
                "Procesos considerados",
            ],
        ],
        colWidths=[67 * mm] * 4,
    )
    sintesis.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 17),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.Color(*_AZUL)),
            ("FONTSIZE", (0, 1), (-1, 1), 7.5),
            ("TEXTCOLOR", (0, 1), (-1, 1), colors.Color(*_GRIS)),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.Color(0.957, 0.969, 0.980)),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.Color(*_BORDE)),
            ("TOPPADDING", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
        ])
    )
    elementos += [sintesis, Spacer(1, 4)]

    # ---------------- Cumplimiento por proceso ----------------
    elementos.append(Paragraph("Cumplimiento por proceso", seccion))

    filas = [["Proceso", "Cumplimiento", "Medidos", "Fuera de meta"]]
    for bloque in resumen:
        promedio = bloque["cumplimiento_promedio"]
        nombre = bloque["nombre"] or ""
        if bloque.get("critico"):
            nombre += "  (crítico)"
        filas.append([
            Paragraph(escape(_recortar(nombre, 70)), celda),
            f"{promedio} %" if promedio is not None else "—",
            f"{bloque['kpis_medidos']} / {bloque['total_kpis']}",
            str(bloque["en_alerta"]),
        ])

    tabla_resumen = Table(
        filas, colWidths=[150 * mm, 40 * mm, 40 * mm, 39 * mm], repeatRows=1
    )
    tabla_resumen.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(*_AZUL_SUAVE)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.Color(*_GRIS)),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.Color(*_BORDE)),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    elementos += [tabla_resumen, Spacer(1, 4)]

    # ---------------- Detalle de indicadores ----------------
    elementos.append(Paragraph("Detalle de indicadores", seccion))

    detalle = [[
        "Indicador", "Proceso", "Valor", "Meta", "Tendencia", "Estado", "Proyección",
    ]]
    estilos_estado = []

    if not indicadores:
        detalle.append([
            Paragraph("No hay indicadores para el alcance seleccionado.", celda),
            "", "", "", "", "", "",
        ])
    else:
        for posicion, k in enumerate(indicadores, start=1):
            contenido = [Paragraph(f"<b>{escape(_recortar(k['nombre'], 62))}</b>", celda)]
            if k.get("formula"):
                contenido.append(
                    Paragraph(escape(_recortar(k["formula"], 82)), celda_menor)
                )

            proyeccion = _formatear(k.get("proyeccion"), k["unidad"])
            if k.get("analisis"):
                proyeccion += f"\nR²={k['analisis']['r2']}"

            detalle.append([
                contenido,
                Paragraph(escape(_recortar(k.get("proceso_nombre") or "—", 34)), celda),
                _formatear(k["valor"], k["unidad"]),
                _formatear(k["meta"], k["unidad"]),
                "Ascendente" if k["tendencia"] == "ascendente" else "Descendente",
                ETIQUETAS_ESTADO.get(k["estado"], "—"),
                proyeccion,
            ])

            color = _COLOR_ESTADO.get(k["estado"])
            if color:
                estilos_estado.append(
                    ("TEXTCOLOR", (5, posicion), (5, posicion), colors.Color(*color))
                )

    tabla_detalle = Table(
        detalle,
        colWidths=[95 * mm, 44 * mm, 24 * mm, 24 * mm, 28 * mm, 30 * mm, 24 * mm],
        repeatRows=1,
    )
    tabla_detalle.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(*_AZUL_SUAVE)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.Color(*_GRIS)),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (5, 1), (5, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (2, 0), (3, -1), "RIGHT"),
            ("ALIGN", (6, 0), (6, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.Color(*_BORDE)),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ] + estilos_estado)
    )
    elementos.append(tabla_detalle)

    def _pie(lienzo, doc):
        """Nota y numeración al pie de cada página."""
        lienzo.saveState()
        lienzo.setFont("Helvetica", 6.5)
        lienzo.setFillColorRGB(*_GRIS)
        lienzo.drawString(
            14 * mm,
            9 * mm,
            "Documento generado automáticamente por el Sistema de Seguimiento de KPIs. "
            "Las proyecciones corresponden a estimaciones estadísticas lineales sobre la "
            "serie histórica. Prototipo académico.",
        )
        lienzo.drawRightString(283 * mm, 9 * mm, f"Página {doc.page}")
        lienzo.restoreState()

    documento.build(elementos, onFirstPage=_pie, onLaterPages=_pie)
    return buffer.getvalue()
