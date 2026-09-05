/* ============================================================
   Cliente de la API REST del backend.
   Centraliza las peticiones y el manejo del token de sesion.
   ============================================================ */

const API = (() => {
  const BASE = "/api";
  const CLAVE_TOKEN = "kpi_token";
  const CLAVE_USUARIO = "kpi_usuario";

  function guardarSesion(token, usuario) {
    localStorage.setItem(CLAVE_TOKEN, token);
    localStorage.setItem(CLAVE_USUARIO, JSON.stringify(usuario));
  }

  function obtenerToken() {
    return localStorage.getItem(CLAVE_TOKEN);
  }

  function obtenerUsuario() {
    try {
      return JSON.parse(localStorage.getItem(CLAVE_USUARIO) || "null");
    } catch {
      return null;
    }
  }

  function cerrarSesion() {
    localStorage.removeItem(CLAVE_TOKEN);
    localStorage.removeItem(CLAVE_USUARIO);
    window.location.href = "login.html";
  }

  async function peticion(ruta, opciones = {}) {
    const cabeceras = opciones.headers || {};
    const token = obtenerToken();
    if (token) cabeceras["Authorization"] = `Bearer ${token}`;

    const respuesta = await fetch(BASE + ruta, { ...opciones, headers: cabeceras });

    // La sesion expiro o el token es invalido
    if (respuesta.status === 401 && !ruta.startsWith("/login")) {
      cerrarSesion();
      throw new Error("Sesión expirada");
    }

    const tipo = respuesta.headers.get("content-type") || "";
    if (!tipo.includes("application/json")) {
      if (!respuesta.ok) throw new Error(`Error ${respuesta.status}`);
      return respuesta.text();
    }

    const datos = await respuesta.json();
    if (!respuesta.ok) throw new Error(datos.error || `Error ${respuesta.status}`);
    return datos;
  }

  return {
    guardarSesion,
    obtenerToken,
    obtenerUsuario,
    cerrarSesion,

    login: (correo, contrasena) =>
      peticion("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ correo, contrasena }),
      }),

    procesos: () => peticion("/procesos"),
    kpis:    (proceso = "general") => peticion(`/kpis?proceso=${encodeURIComponent(proceso)}`),
    resumen: () => peticion("/resumen"),
    alertas: () => peticion("/alertas"),

    /* Notifica al responsable del proceso una desviación de desempeño (RF7) */
    notificar: (idKpi) =>
      peticion("/notificar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_kpi: idKpi }),
      }),

    notificaciones: () => peticion("/notificaciones"),

    /* Registro de incidencias técnicas del sistema (RF8) */
    registrarIncidencia: (datos) =>
      peticion("/incidencias", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos),
      }),

    incidencias: () => peticion("/incidencias"),

    cargarArchivo: (proceso, archivo) => {
      const cuerpo = new FormData();
      cuerpo.append("proceso", proceso);
      cuerpo.append("archivo", archivo);
      return peticion("/carga", { method: "POST", body: cuerpo });
    },

    /* Descarga el reporte consolidado como archivo PDF (RF6) */
    descargarPdf: async (proceso) => {
      const respuesta = await fetch(
        `${BASE}/reporte.pdf?proceso=${encodeURIComponent(proceso)}`,
        { headers: { Authorization: `Bearer ${obtenerToken()}` } }
      );

      if (!respuesta.ok) {
        let detalle = "No se pudo generar el reporte";
        try {
          detalle = (await respuesta.json()).error || detalle;
        } catch {
          // La respuesta no traía un mensaje aprovechable
        }
        throw new Error(detalle);
      }

      const blob = await respuesta.blob();
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      const fecha = new Date().toISOString().slice(0, 10).replace(/-/g, "");

      enlace.href = url;
      enlace.download = `reporte_kpis_${proceso}_${fecha}.pdf`;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(url);
    },

    /* Abre el reporte en pantalla, para consultarlo sin descargarlo.
       Se solicita por fetch porque requiere el token. */
    abrirReporte: async (proceso) => {
      const respuesta = await fetch(
        `${BASE}/reporte?proceso=${encodeURIComponent(proceso)}`,
        { headers: { Authorization: `Bearer ${obtenerToken()}` } }
      );
      if (!respuesta.ok) throw new Error("No se pudo generar el reporte");

      const html = await respuesta.text();
      const ventana = window.open("", "_blank");
      if (!ventana) {
        throw new Error(
          "El navegador bloqueó la ventana emergente. Permítala para ver el reporte."
        );
      }
      ventana.document.write(html);
      ventana.document.close();
    },

    /* La descarga necesita el token, por eso se hace por fetch y no por enlace directo */
    descargarCsv: async (proceso) => {
      const respuesta = await fetch(`${BASE}/exportar?proceso=${encodeURIComponent(proceso)}`, {
        headers: { Authorization: `Bearer ${obtenerToken()}` },
      });
      if (!respuesta.ok) throw new Error("No se pudo generar el archivo");

      const blob = await respuesta.blob();
      const url = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = `kpis_${proceso}.csv`;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(url);
    },
  };
})();
