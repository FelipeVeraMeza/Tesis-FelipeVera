"""
Capa de aplicacion: API REST en Flask.

Expone los endpoints que consume la interfaz web y sirve tambien los archivos
estaticos del frontend, de modo que todo el prototipo se levanta con un solo
comando.
"""
import csv
from datetime import datetime
import io

from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS

from . import auth, conectores, config, db, etl, kpi, notificaciones, reportes


def crear_app() -> Flask:
    config.validar_configuracion()

    app = Flask(
        __name__,
        static_folder=str(config.FRONTEND_DIR),
        static_url_path="",
    )
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB por archivo
    CORS(app)

    # --------------------------------------------------------------
    # Frontend
    # --------------------------------------------------------------
    @app.route("/")
    def inicio():
        return send_from_directory(config.FRONTEND_DIR, "login.html")

    # --------------------------------------------------------------
    # Estado del sistema
    # --------------------------------------------------------------
    @app.get("/api/salud")
    def salud():
        return jsonify(db.probar_conexion())

    # --------------------------------------------------------------
    # Autenticacion (RF4)
    # --------------------------------------------------------------
    @app.post("/api/login")
    def login():
        datos = request.get_json(silent=True) or {}
        correo = datos.get("correo", "")
        contrasena = datos.get("contrasena", "")

        if not correo or not contrasena:
            return jsonify({"error": "Debe ingresar correo y contrasena"}), 400

        usuario = auth.autenticar(correo, contrasena)
        if not usuario:
            return jsonify({"error": "Credenciales invalidas"}), 401

        return jsonify(
            {
                "token": auth.generar_token(usuario),
                "usuario": {
                    "nombre": usuario["nombre_usuario"],
                    "correo": usuario["correo"],
                    "rol": usuario["rol"],
                    "permisos": usuario["permisos"],
                },
            }
        )

    @app.get("/api/sesion")
    @auth.requiere_sesion
    def sesion():
        return jsonify(g.usuario)

    # --------------------------------------------------------------
    # Consulta de indicadores (RF5, RF9)
    # --------------------------------------------------------------
    @app.get("/api/procesos")
    @auth.requiere_sesion
    def procesos():
        return jsonify(
            db.seleccionar(
                "proceso_ti",
                {
                    "select": "id_proceso,nombre_proceso,codigo_proceso,descripcion,"
                    "responsable,estado,critico",
                    "order": "nombre_proceso",
                },
            )
        )

    @app.get("/api/kpis")
    @auth.requiere_sesion
    def kpis():
        proceso = request.args.get("proceso", "general")
        return jsonify(kpi.obtener_kpis(proceso))

    @app.get("/api/resumen")
    @auth.requiere_sesion
    def resumen():
        return jsonify(kpi.resumen_por_proceso())

    @app.get("/api/estado-general")
    @auth.requiere_sesion
    def estado_general():
        """Sintesis del desempeno para el encabezado del panel."""
        proceso = request.args.get("proceso", "general")
        return jsonify(kpi.estado_general(proceso))

    @app.get("/api/evolucion")
    @auth.requiere_sesion
    def evolucion():
        """Cumplimiento promedio por periodo, para el grafico de evolucion."""
        proceso = request.args.get("proceso", "general")
        return jsonify(kpi.evolucion_cumplimiento(proceso))

    @app.get("/api/periodos")
    @auth.requiere_sesion
    def periodos():
        return jsonify(kpi.periodos_disponibles())

    # --------------------------------------------------------------
    # Alertas automaticas (RF7)
    # --------------------------------------------------------------
    @app.get("/api/alertas")
    @auth.requiere_sesion
    def alertas():
        solo_criticos = request.args.get("criticos", "").lower() in ("1", "true", "si")
        return jsonify(kpi.alertas(solo_criticos=solo_criticos))

    @app.post("/api/notificar")
    @auth.requiere_rol("Gerente", "Lider", "Administrador")
    def notificar():
        """Emite una alerta al responsable del proceso (RF7)."""
        datos = request.get_json(silent=True) or {}
        id_kpi = datos.get("id_kpi")

        if not isinstance(id_kpi, int):
            return jsonify({"error": "Debe indicar el identificador del indicador"}), 400

        try:
            resultado = notificaciones.emitir(id_kpi, g.usuario)
        except notificaciones.ErrorNotificacion as exc:
            return jsonify({"error": str(exc)}), 422

        return jsonify(resultado)

    @app.get("/api/notificaciones")
    @auth.requiere_sesion
    def listar_notificaciones():
        return jsonify(notificaciones.historial())

    # --------------------------------------------------------------
    # Carga de archivos y ETL (RF1, RF2, RF3)
    # --------------------------------------------------------------
    @app.post("/api/carga")
    @auth.requiere_rol("Analista", "Administrador")
    def carga():
        proceso = request.form.get("proceso", "")
        archivo = request.files.get("archivo")

        if proceso not in config.PROCESOS_CRITICOS:
            return jsonify(
                {"error": f"Proceso invalido. Use uno de: {', '.join(config.PROCESOS_CRITICOS)}"}
            ), 400
        if archivo is None or not archivo.filename:
            return jsonify({"error": "No se recibio ningun archivo"}), 400

        nombre = archivo.filename.lower()
        if not nombre.endswith((".csv", ".xlsx", ".xlsm")):
            return jsonify(
                {"error": "El archivo debe estar en formato CSV o Excel (.csv, .xlsx)"}
            ), 400

        crudo = archivo.read()

        # Las planillas se convierten a CSV para que el ETL opere de una
        # sola forma, cualquiera sea el formato de origen (RF1)
        if nombre.endswith((".xlsx", ".xlsm")):
            try:
                contenido = etl.convertir_excel(crudo)
            except etl.ErrorETL as exc:
                return jsonify({"error": str(exc)}), 422
        else:
            try:
                contenido = crudo.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    # Excel en Windows suele exportar en esta codificacion
                    contenido = crudo.decode("latin-1")
                except UnicodeDecodeError:
                    return jsonify(
                        {"error": "No se pudo leer el archivo. Guardelo con codificacion UTF-8."}
                    ), 400

        try:
            resultado = etl.procesar_archivo(
                contenido,
                proceso,
                archivo.filename,
                usuario=g.usuario,
                tipo_fuente="Excel" if nombre.endswith((".xlsx", ".xlsm")) else "CSV",
            )
        except etl.ErrorETL as exc:
            return jsonify({"error": str(exc)}), 422
        except db.ErrorBaseDatos as exc:
            return jsonify({"error": f"Error al guardar en la base de datos: {exc}"}), 500

        return jsonify(resultado)

    @app.get("/api/cargas")
    @auth.requiere_sesion
    def historial_cargas():
        """Historial de cargas realizadas, con su trazabilidad."""
        filas = db.seleccionar(
            "fuente_dato",
            {
                "select": "id_fuente,nombre_fuente,tipo_fuente,proceso,"
                "filas_procesadas,periodos_cargados,advertencias,fecha_carga,"
                "usuario(nombre_usuario)",
                "order": "fecha_carga.desc",
                "limit": "100",
            },
        )
        return jsonify(
            [
                {
                    "id_fuente": f["id_fuente"],
                    "archivo": f["nombre_fuente"],
                    "tipo": f["tipo_fuente"],
                    "proceso": f["proceso"],
                    "filas": f["filas_procesadas"],
                    "periodos": f["periodos_cargados"],
                    "advertencias": f["advertencias"],
                    "fecha": f["fecha_carga"],
                    "responsable": (f.get("usuario") or {}).get("nombre_usuario"),
                }
                for f in filas
            ]
        )

    # --------------------------------------------------------------
    # Exportacion de resultados (RF6)
    # --------------------------------------------------------------
    @app.get("/api/exportar")
    @auth.requiere_sesion
    def exportar():
        proceso = request.args.get("proceso", "general")
        datos = kpi.obtener_kpis(proceso)

        buffer = io.StringIO()
        escritor = csv.writer(buffer, delimiter=";")
        escritor.writerow(
            ["Proceso", "KPI", "Descripcion", "Formula", "Valor", "Meta",
             "Unidad", "Tendencia", "Estado", "Cumplimiento %", "Proyeccion"]
        )
        for k in datos:
            escritor.writerow(
                [
                    k["proceso_nombre"], k["nombre"], k["descripcion"], k["formula"],
                    k["valor"], k["meta"], k["unidad"], k["tendencia"],
                    k["estado"], k["cumplimiento"], k["proyeccion"],
                ]
            )

        return (
            buffer.getvalue(),
            200,
            {
                "Content-Type": "text/csv; charset=utf-8",
                "Content-Disposition": f'attachment; filename="kpis_{proceso}.csv"',
            },
        )

    @app.get("/api/reporte")
    @auth.requiere_sesion
    def reporte():
        """Reporte consolidado en HTML, para consulta en pantalla (RF6)."""
        proceso = request.args.get("proceso", "general")
        return (
            reportes.generar_html(
                kpi.obtener_kpis(proceso),
                kpi.resumen_por_proceso(),
                proceso,
                g.usuario,
            ),
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )

    @app.get("/api/reporte.pdf")
    @auth.requiere_sesion
    def reporte_pdf():
        """Reporte consolidado como archivo PDF descargable (RF6)."""
        proceso = request.args.get("proceso", "general")

        try:
            documento = reportes.generar_pdf(
                kpi.obtener_kpis(proceso),
                kpi.resumen_por_proceso(),
                proceso,
                g.usuario,
            )
        except ImportError:
            return jsonify(
                {
                    "error": "La generacion de PDF requiere la biblioteca reportlab. "
                    "Ejecute: pip install reportlab"
                }
            ), 501

        marca = datetime.now().strftime("%Y%m%d")
        return (
            documento,
            200,
            {
                "Content-Type": "application/pdf",
                "Content-Disposition": (
                    f'attachment; filename="reporte_kpis_{proceso}_{marca}.pdf"'
                ),
            },
        )

    # --------------------------------------------------------------
    # Conectores a fuentes externas
    # --------------------------------------------------------------
    @app.get("/api/conectores")
    @auth.requiere_sesion
    def listar_conectores():
        """Situacion de las fuentes de datos configuradas."""
        return jsonify(conectores.estado())

    @app.post("/api/sincronizar")
    @auth.requiere_rol("Analista", "Administrador")
    def sincronizar():
        """
        Extrae los datos de un periodo directamente desde la fuente externa,
        sin requerir la carga manual de un archivo.
        """
        datos = request.get_json(silent=True) or {}
        proceso = (datos.get("proceso") or "").strip()
        periodo = (datos.get("periodo") or "").strip()
        fuente = (datos.get("fuente") or "jira").strip()

        if proceso not in config.PROCESOS_CRITICOS:
            return jsonify(
                {"error": f"Proceso invalido. Use uno de: {', '.join(config.PROCESOS_CRITICOS)}"}
            ), 400
        if not etl.PATRON_PERIODO.match(periodo):
            return jsonify({"error": "Indique el periodo en formato AAAA-MM"}), 400

        try:
            conector = conectores.obtener(fuente)
            fila = conector.extraer(proceso, periodo)
        except conectores.ErrorConector as exc:
            return jsonify({"error": str(exc)}), 422

        # Los datos extraidos siguen el mismo camino que un archivo cargado
        columnas = etl.COLUMNAS_ESPERADAS[proceso]
        encabezado = ",".join(columnas)
        valores = ",".join(str(fila.get(c, 0)) for c in columnas)

        try:
            resultado = etl.procesar_archivo(
                f"{encabezado}\n{valores}\n",
                proceso,
                f"{conector.nombre} · {periodo}",
                usuario=g.usuario,
                tipo_fuente="Sistema externo",
            )
        except etl.ErrorETL as exc:
            return jsonify({"error": str(exc)}), 422

        resultado["fuente"] = conector.nombre
        resultado["datos_extraidos"] = fila
        return jsonify(resultado)

    # --------------------------------------------------------------
    # Registro de incidencias tecnicas (RF8)
    # --------------------------------------------------------------
    MODULOS = ("Dashboard", "Carga de datos", "Reportes", "Alertas", "Otro")
    SEVERIDADES = ("Alta", "Media", "Baja")

    @app.post("/api/incidencias")
    @auth.requiere_sesion
    def registrar_incidencia():
        """Permite a cualquier usuario reportar una falla del sistema."""
        datos = request.get_json(silent=True) or {}

        titulo = (datos.get("titulo") or "").strip()
        descripcion = (datos.get("descripcion") or "").strip()
        modulo = (datos.get("modulo") or "Otro").strip()
        severidad = (datos.get("severidad") or "Media").strip()

        if len(titulo) < 5:
            return jsonify({"error": "Indique un titulo de al menos 5 caracteres"}), 400
        if len(descripcion) < 10:
            return jsonify(
                {"error": "Describa la incidencia con al menos 10 caracteres"}
            ), 400
        if modulo not in MODULOS:
            return jsonify({"error": f"Modulo invalido. Use uno de: {', '.join(MODULOS)}"}), 400
        if severidad not in SEVERIDADES:
            severidad = "Media"

        registro = db.insertar(
            "incidencia",
            {
                "id_usuario": g.usuario.get("id_usuario"),
                "modulo": modulo,
                "severidad": severidad,
                "titulo": titulo[:150],
                "descripcion": descripcion[:1000],
            },
        )

        return jsonify(
            {
                "id_incidencia": registro[0]["id_incidencia"] if registro else None,
                "estado": "Abierta",
                "mensaje": "La incidencia fue registrada correctamente.",
            }
        ), 201

    @app.get("/api/incidencias")
    @auth.requiere_sesion
    def listar_incidencias():
        filas = db.seleccionar(
            "incidencia",
            {
                "select": "id_incidencia,modulo,severidad,titulo,descripcion,"
                "estado,fecha_reporte,usuario(nombre_usuario)",
                "order": "fecha_reporte.desc",
                "limit": "100",
            },
        )
        return jsonify(
            [
                {
                    "id_incidencia": f["id_incidencia"],
                    "modulo": f["modulo"],
                    "severidad": f["severidad"],
                    "titulo": f["titulo"],
                    "descripcion": f["descripcion"],
                    "estado": f["estado"],
                    "fecha": f["fecha_reporte"],
                    "reportada_por": (f.get("usuario") or {}).get("nombre_usuario"),
                }
                for f in filas
            ]
        )

    # --------------------------------------------------------------
    # Manejo de errores
    # --------------------------------------------------------------
    @app.errorhandler(db.ErrorBaseDatos)
    def error_bd(exc):
        return jsonify({"error": f"Error de base de datos: {exc}"}), 500

    @app.errorhandler(404)
    def no_encontrado(_):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Recurso no encontrado"}), 404
        return send_from_directory(config.FRONTEND_DIR, "login.html")

    return app
