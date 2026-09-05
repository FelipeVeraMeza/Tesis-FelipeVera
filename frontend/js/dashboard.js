/* ============================================================
   Panel de control de KPIs
   Visualizacion adaptada al perfil del usuario (RF5), alertas
   automaticas (RF7), carga de datos (RF1) y exportacion (RF6).
   ============================================================ */

const usuario = API.obtenerUsuario();
if (!API.obtenerToken() || !usuario) {
  window.location.replace("login.html");
}

const ETIQUETAS_ESTADO = {
  cumple:    "Cumple",
  riesgo:    "En riesgo",
  bajo:      "Bajo desempeño",
  sin_datos: "Sin datos",
};

const COLORES = {
  azul:  "#0f4c75",
  verde: "#2e9e5b",
  ambar: "#d99411",
  rojo:  "#d64545",
};

const PERMISOS = usuario.permisos || {};

// El envío de alertas corresponde al Gerente y al Líder de TI (RF7)
const PUEDE_NOTIFICAR = PERMISOS.puede_notificar === true;

/* Enfoque del panel según el perfil, conforme a los usuarios definidos
   en el alcance del proyecto (RF5). */
/* Los dashboards se organizan en dos niveles jerárquicos:

   - Nivel estratégico: dirigido a la Gerencia de TI, integra la
     información global de los procesos.
   - Nivel táctico: orientado a los responsables de proceso, con el
     detalle por tipo de gestión. */
const VISTAS = {
  ejecutiva: {
    titulo: "Vista ejecutiva",
    descripcion: "Estado global de los procesos y cumplimiento de objetivos estratégicos",
    nivel: "estratégico",
    soloCriticos: true,
  },
  consolidada: {
    titulo: "Dashboard consolidado",
    descripcion: "Cumplimiento, desviaciones y tendencias de los últimos períodos",
    nivel: "táctico",
    soloCriticos: true,
  },
  detallada: {
    titulo: "Panel de análisis",
    descripcion: "Carga de datos, validación y resultados detallados por indicador",
    nivel: "táctico",
    soloCriticos: false,
  },
  administracion: {
    titulo: "Panel de administración",
    descripcion: "Catálogo completo de procesos e indicadores del sistema",
    nivel: "estratégico",
    soloCriticos: false,
  },
};

const VISTA = VISTAS[PERMISOS.vista] || VISTAS.detallada;

let kpisActuales = [];
let grafico = null;
let kpiEnAlerta = null;

/* ------------------------------------------------------------
   Selector de procesos

   El catálogo proviene del levantamiento realizado en la Gerencia
   de TI, por lo que las opciones se construyen desde la base de
   datos y no se fijan en el HTML.
   ------------------------------------------------------------ */
async function cargarSelectorProcesos() {
  const selector = document.getElementById("selectorProceso");

  try {
    const procesos = await API.procesos();

    const criticos = procesos.filter((p) => p.critico);
    const resto = procesos.filter((p) => !p.critico);

    const opciones = (lista) =>
      lista
        .map((p) => `<option value="${p.codigo_proceso}">${p.nombre_proceso}</option>`)
        .join("");

    // Los perfiles ejecutivo y consolidado se centran en los procesos
    // críticos; el resto del catálogo queda accesible igualmente
    const etiquetaGeneral = VISTA.soloCriticos
      ? "Procesos críticos"
      : "Todos los procesos";

    selector.innerHTML =
      `<option value="${VISTA.soloCriticos ? "criticos" : "general"}" selected>${etiquetaGeneral}</option>` +
      (VISTA.soloCriticos
        ? '<option value="general">Todos los procesos</option>'
        : "") +
      (criticos.length
        ? `<optgroup label="Procesos críticos">${opciones(criticos)}</optgroup>`
        : "") +
      (resto.length
        ? `<optgroup label="Otros procesos">${opciones(resto)}</optgroup>`
        : "");
  } catch {
    // Si falla, el selector conserva la opción general
  }
}

/* ------------------------------------------------------------
   Utilidades de formato
   ------------------------------------------------------------ */
function formatearValor(valor, unidad) {
  if (valor === null || valor === undefined) return "—";
  const numero = Number(valor);
  const texto = Number.isInteger(numero) ? numero.toString() : numero.toFixed(2);
  if (unidad === "%") return `${texto} %`;
  if (unidad === "cantidad") return texto;
  return `${texto} ${unidad || ""}`.trim();
}

function colorEstado(estado) {
  return { cumple: COLORES.verde, riesgo: COLORES.ambar, bajo: COLORES.rojo }[estado] || COLORES.azul;
}

/* ------------------------------------------------------------
   Encabezado y permisos
   ------------------------------------------------------------ */
function prepararSesion() {
  document.getElementById("usuarioNombre").textContent = usuario.nombre;
  document.getElementById("usuarioRol").textContent = usuario.rol;

  // El encabezado identifica el enfoque del panel y su nivel jerárquico
  document.getElementById("tituloVista").textContent = VISTA.titulo;
  document.getElementById("descripcionVista").textContent = VISTA.descripcion;
  document.getElementById("nivelVista").textContent = `Nivel ${VISTA.nivel}`;

  // La carga de archivos solo está disponible para quien tiene ese permiso
  if (PERMISOS.puede_cargar) {
    document.getElementById("seccionCarga").classList.remove("oculto");
  }

  if (!PERMISOS.puede_exportar) {
    document.getElementById("btnExportar").classList.add("oculto");
  }

  // Los perfiles con foco en los procesos críticos parten con esa vista
  if (VISTA.soloCriticos) {
    document.getElementById("selectorProceso").dataset.foco = "criticos";
  }
}

/* ------------------------------------------------------------
   Tarjetas de cumplimiento por proceso
   ------------------------------------------------------------ */
function pintarResumen(resumen) {
  const contenedor = document.getElementById("tarjetasResumen");

  if (!resumen.length) {
    contenedor.innerHTML =
      '<p class="estado-carga">No hay procesos registrados en la base de datos.</p>';
    return;
  }

  // Con el catálogo completo, el panel destaca los procesos críticos
  const criticos = resumen.filter((b) => b.critico);
  const visibles = criticos.length ? criticos : resumen;

  contenedor.innerHTML = visibles
    .map((bloque) => {
      const promedio = bloque.cumplimiento_promedio;
      let clase = "";
      if (promedio !== null) {
        clase = promedio >= 90 ? "cumple" : promedio >= 75 ? "riesgo" : "bajo";
      }

      let detalle;
      if (bloque.kpis_medidos === 0) {
        detalle = `Sin mediciones · ${bloque.total_kpis} indicadores definidos`;
      } else if (bloque.en_alerta > 0) {
        detalle = `${bloque.en_alerta} de ${bloque.kpis_medidos} indicadores fuera de meta`;
      } else {
        detalle = `${bloque.kpis_medidos} indicadores dentro de meta`;
      }

      const cobertura =
        bloque.kpis_medidos < bloque.total_kpis
          ? `<span class="tarjeta-cobertura">${bloque.kpis_medidos}/${bloque.total_kpis} medidos</span>`
          : "";

      return `
        <article class="tarjeta ${clase}">
          <h3>${bloque.nombre}</h3>
          <p class="tarjeta-valor">${promedio !== null ? promedio + " %" : "—"}</p>
          <span class="tarjeta-detalle">${detalle}</span>
          ${cobertura}
        </article>`;
    })
    .join("");
}

/* ------------------------------------------------------------
   Alertas automaticas (RF7)
   ------------------------------------------------------------ */
function pintarAlertas(alertas) {
  const panel = document.getElementById("panelAlertas");
  const lista = document.getElementById("listaAlertas");

  if (!alertas.length) {
    panel.classList.add("oculto");
    return;
  }

  lista.innerHTML = alertas
    .map((a) => {
      const boton = PUEDE_NOTIFICAR
        ? `<button class="btn-sirena ${a.estado === "bajo" ? "severa" : ""}"
                   data-alerta-kpi="${a.id_kpi}"
                   title="Notificar a ${a.dueno_proceso || "el responsable"}"
                   aria-label="Notificar desviación de ${a.kpi}">🚨</button>`
        : "";

      return `<li>
        <strong>${a.proceso}</strong> · ${a.kpi}: ${formatearValor(a.valor, a.unidad)}
        (meta ${formatearValor(a.meta, a.unidad)}) — ${ETIQUETAS_ESTADO[a.estado]}
        ${boton}
      </li>`;
    })
    .join("");

  panel.classList.remove("oculto");
}

/* ------------------------------------------------------------
   Tabla de indicadores
   ------------------------------------------------------------ */
function pintarTabla(kpis) {
  const cuerpo = document.querySelector("#tablaKpis tbody");
  const contador = document.getElementById("contadorKpis");
  const soloMedidos = document.getElementById("soloMedidos").checked;

  const visibles = soloMedidos ? kpis.filter((k) => k.estado !== "sin_datos") : kpis;
  const medidos = kpis.filter((k) => k.estado !== "sin_datos").length;

  contador.textContent =
    `${medidos} de ${kpis.length} indicadores con medición registrada`;

  if (!visibles.length) {
    cuerpo.innerHTML = `<tr><td colspan="9" class="estado-carga">${
      kpis.length
        ? "Ningún indicador de este proceso tiene mediciones registradas."
        : "No hay indicadores para este proceso."
    }</td></tr>`;
    return;
  }

  cuerpo.innerHTML = visibles
    .map((kpi) => {
      const flecha = kpi.tendencia === "ascendente" ? "↑ Mayor es mejor" : "↓ Menor es mejor";
      const indice = kpisActuales.indexOf(kpi);

      // Los indicadores aún no implementados se distinguen del resto
      const implementado = (kpi.estado_implementacion || "").toLowerCase() === "implementado";
      const marca = implementado
        ? ""
        : `<span class="insignia tenue" title="${
            kpi.viable === "Si" ? "Viable, pendiente de implementación" : "No viable de medir"
          }">${kpi.viable === "Si" ? "Pendiente" : "No viable"}</span>`;

      // El control de alerta aparece solo ante desviaciones, y solo para
      // quienes tienen atribución para notificar al responsable
      const desviado = kpi.estado === "riesgo" || kpi.estado === "bajo";
      const alerta =
        desviado && PUEDE_NOTIFICAR
          ? `<button class="btn-sirena ${kpi.estado === "bajo" ? "severa" : ""}"
                     data-alerta="${indice}"
                     title="Notificar al responsable del proceso"
                     aria-label="Notificar desviación de ${kpi.nombre}">🚨</button>`
          : desviado
          ? '<span class="sin-alerta" title="Indicador fuera de meta">🚨</span>'
          : '<span class="sin-alerta">—</span>';

      return `
        <tr>
          <td class="celda-indicador">
            <strong>${kpi.nombre}</strong>
            <small>${kpi.descripcion || kpi.formula || ""}</small>
          </td>
          <td>
            <span class="insignia">${kpi.proceso_nombre || "—"}</span>
            ${marca}
          </td>
          <td class="valor-numerico">${formatearValor(kpi.valor, kpi.unidad)}</td>
          <td class="valor-numerico">${formatearValor(kpi.meta, kpi.unidad)}</td>
          <td>${flecha}</td>
          <td><span class="estado ${kpi.estado}">${ETIQUETAS_ESTADO[kpi.estado]}</span></td>
          <td class="valor-numerico">
            ${formatearValor(kpi.proyeccion, kpi.unidad)}
            ${kpi.analisis
              ? `<small class="confianza ${kpi.analisis.confiabilidad}"
                        title="Ajuste de la tendencia: R²=${kpi.analisis.r2} sobre ${kpi.analisis.periodos} períodos">
                   ${kpi.analisis.confiabilidad}
                 </small>`
              : ""}
          </td>
          <td>${alerta}</td>
          <td>
            ${kpi.historico.length
              ? `<button class="btn-secundario" data-indice="${indice}">Ver gráfico</button>`
              : ""}
          </td>
        </tr>`;
    })
    .join("");
}

/* ------------------------------------------------------------
   Notificación de desviaciones (RF7)

   Al accionar el control de alerta se despliega una ventana modal
   que identifica el indicador y su proceso, y solicita confirmación
   antes de notificar al responsable.
   ------------------------------------------------------------ */
function abrirModalAlerta(kpi) {
  kpiEnAlerta = kpi;

  document.getElementById("alertaKpi").textContent = kpi.nombre;
  document.getElementById("alertaProceso").textContent = kpi.proceso_nombre || "—";
  document.getElementById("alertaValor").textContent = formatearValor(kpi.valor, kpi.unidad);
  document.getElementById("alertaMeta").textContent = formatearValor(kpi.meta, kpi.unidad);
  document.getElementById("alertaDestinatario").textContent =
    kpi.dueno_proceso || kpi.proceso_nombre || "Gerencia de TI";

  const estado = document.getElementById("alertaEstado");
  estado.innerHTML = `<span class="estado ${kpi.estado}">${ETIQUETAS_ESTADO[kpi.estado]}</span>`;

  // Se parte siempre desde el paso de confirmación
  document.getElementById("modalConfirmacion").classList.remove("oculto");
  document.getElementById("modalResultado").classList.add("oculto");
  document.getElementById("modalError").textContent = "";

  const confirmar = document.getElementById("modalConfirmar");
  confirmar.classList.remove("oculto");
  confirmar.disabled = false;
  confirmar.textContent = "Enviar notificación";
  document.getElementById("modalCancelar").textContent = "Cancelar";

  document.getElementById("modalAlerta").classList.remove("oculto");
  confirmar.focus();
}

function cerrarModalAlerta() {
  document.getElementById("modalAlerta").classList.add("oculto");
  kpiEnAlerta = null;
}

async function confirmarNotificacion() {
  if (!kpiEnAlerta) return;

  const boton = document.getElementById("modalConfirmar");
  const error = document.getElementById("modalError");

  boton.disabled = true;
  boton.textContent = "Enviando…";
  error.textContent = "";

  try {
    const respuesta = await API.notificar(kpiEnAlerta.id_kpi);

    document.getElementById("resultadoDetalle").textContent =
      `Se notificó a ${respuesta.destinatario} sobre la desviación del indicador ` +
      `«${respuesta.kpi}»` +
      (respuesta.simulada
        ? ". El envío por correo se encuentra simulado en esta etapa de prototipo."
        : ".");

    document.getElementById("resultadoMensaje").textContent = respuesta.mensaje;

    document.getElementById("modalConfirmacion").classList.add("oculto");
    document.getElementById("modalResultado").classList.remove("oculto");

    boton.classList.add("oculto");
    document.getElementById("modalCancelar").textContent = "Cerrar";
  } catch (excepcion) {
    error.textContent = excepcion.message;
    boton.disabled = false;
    boton.textContent = "Enviar notificación";
  }
}

/* ------------------------------------------------------------
   Registro de incidencias técnicas (RF8)
   ------------------------------------------------------------ */
function abrirModalIncidencia() {
  document.getElementById("incidenciaFormulario").classList.remove("oculto");
  document.getElementById("incidenciaResultado").classList.add("oculto");
  document.getElementById("incidenciaError").textContent = "";

  document.getElementById("incidenciaTituloCampo").value = "";
  document.getElementById("incidenciaDescripcion").value = "";

  const enviar = document.getElementById("incidenciaEnviar");
  enviar.classList.remove("oculto");
  enviar.disabled = false;
  enviar.textContent = "Registrar incidencia";
  document.getElementById("incidenciaCancelar").textContent = "Cancelar";

  document.getElementById("modalIncidencia").classList.remove("oculto");
  document.getElementById("incidenciaTituloCampo").focus();
}

function cerrarModalIncidencia() {
  document.getElementById("modalIncidencia").classList.add("oculto");
}

async function enviarIncidencia() {
  const enviar = document.getElementById("incidenciaEnviar");
  const error = document.getElementById("incidenciaError");

  const datos = {
    modulo: document.getElementById("incidenciaModulo").value,
    severidad: document.getElementById("incidenciaSeveridad").value,
    titulo: document.getElementById("incidenciaTituloCampo").value.trim(),
    descripcion: document.getElementById("incidenciaDescripcion").value.trim(),
  };

  // Se valida en el cliente para dar respuesta inmediata; el servidor
  // vuelve a comprobarlo antes de registrar
  if (datos.titulo.length < 5) {
    error.textContent = "Indique un título de al menos 5 caracteres.";
    return;
  }
  if (datos.descripcion.length < 10) {
    error.textContent = "Describa la incidencia con al menos 10 caracteres.";
    return;
  }

  enviar.disabled = true;
  enviar.textContent = "Registrando…";
  error.textContent = "";

  try {
    const respuesta = await API.registrarIncidencia(datos);

    document.getElementById("incidenciaDetalle").textContent =
      `La incidencia N.º ${respuesta.id_incidencia} quedó registrada en estado ` +
      `${respuesta.estado} y será revisada por el administrador del sistema.`;

    document.getElementById("incidenciaFormulario").classList.add("oculto");
    document.getElementById("incidenciaResultado").classList.remove("oculto");

    enviar.classList.add("oculto");
    document.getElementById("incidenciaCancelar").textContent = "Cerrar";
  } catch (excepcion) {
    error.textContent = excepcion.message;
    enviar.disabled = false;
    enviar.textContent = "Registrar incidencia";
  }
}

/* ------------------------------------------------------------
   Grafico del indicador seleccionado
   ------------------------------------------------------------ */
function mostrarGrafico(kpi) {
  const seccion = document.getElementById("seccionGrafico");
  const lienzo = document.getElementById("lienzoGrafico");

  document.getElementById("tituloGrafico").textContent = `Evolución · ${kpi.nombre}`;

  // Al detalle del indicador se suma la lectura estadística de su serie
  const a = kpi.analisis;
  const analisis = a
    ? ` — Tendencia ${a.direccion}, variación de ${a.pendiente > 0 ? "+" : ""}${a.pendiente} ` +
      `por período sobre ${a.periodos} mediciones (R²=${a.r2}, confiabilidad ${a.confiabilidad})`
    : " — Serie insuficiente para estimar una tendencia";

  document.getElementById("detalleGrafico").textContent =
    `Fórmula: ${kpi.formula || "—"} · Unidad: ${kpi.unidad || "—"} · ` +
    `Periodicidad: ${kpi.periodicidad || "—"}${analisis}`;

  if (grafico) grafico.destroy();

  const etiquetas = kpi.historico.map((p) => p.periodo);
  const valores = kpi.historico.map((p) => p.valor);

  // La proyeccion se dibuja como un punto adicional al final de la serie
  const conProyeccion = kpi.proyeccion !== null && kpi.proyeccion !== undefined;
  const serieProyectada = conProyeccion
    ? [...Array(valores.length - 1).fill(null), valores.at(-1), kpi.proyeccion]
    : [];

  const conjuntos = [
    {
      label: kpi.nombre,
      data: valores,
      borderColor: colorEstado(kpi.estado),
      backgroundColor: "rgba(15, 76, 117, .12)",
      tension: 0.3,
      fill: true,
      pointRadius: 4,
    },
  ];

  if (kpi.meta !== null) {
    conjuntos.push({
      label: "Meta",
      data: Array(etiquetas.length + (conProyeccion ? 1 : 0)).fill(kpi.meta),
      borderColor: COLORES.ambar,
      borderDash: [6, 4],
      pointRadius: 0,
      fill: false,
    });
  }

  if (conProyeccion) {
    conjuntos.push({
      label: "Proyección",
      data: serieProyectada,
      borderColor: COLORES.azul,
      borderDash: [3, 3],
      pointRadius: 4,
      pointStyle: "triangle",
      fill: false,
    });
  }

  grafico = new Chart(lienzo.getContext("2d"), {
    type: kpi.tipo_grafico === "bar" && kpi.historico.length === 1 ? "bar" : "line",
    data: {
      labels: conProyeccion ? [...etiquetas, "Proyectado"] : etiquetas,
      datasets: conjuntos,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8 } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${formatearValor(ctx.parsed.y, kpi.unidad)}`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: kpi.unidad || "" },
        },
      },
    },
  });

  seccion.classList.remove("oculto");
  seccion.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* ------------------------------------------------------------
   Carga de datos desde el servidor
   ------------------------------------------------------------ */
async function cargarDatos() {
  const selector = document.getElementById("selectorProceso");
  const proceso = selector.value;
  const nombreProceso = selector.options[selector.selectedIndex]?.textContent || "";

  document.getElementById("tituloDetalle").textContent =
    proceso === "general" || proceso === "criticos"
      ? `Detalle de indicadores · ${nombreProceso.toLowerCase()}`
      : `Detalle de indicadores · ${nombreProceso}`;

  try {
    const [kpis, resumen, alertas] = await Promise.all([
      API.kpis(proceso),
      API.resumen(),
      API.alertas(),
    ]);

    kpisActuales = kpis;
    pintarResumen(resumen);
    pintarAlertas(alertas);
    pintarTabla(kpis);
  } catch (error) {
    document.querySelector("#tablaKpis tbody").innerHTML =
      `<tr><td colspan="9" class="estado-carga">No se pudieron obtener los datos: ${error.message}</td></tr>`;
    document.getElementById("tarjetasResumen").innerHTML =
      '<p class="estado-carga">Sin conexión con el servidor.</p>';
  }
}

/* ------------------------------------------------------------
   Eventos
   ------------------------------------------------------------ */
document.getElementById("selectorProceso").addEventListener("change", () => {
  document.getElementById("seccionGrafico").classList.add("oculto");
  cargarDatos();
});

document.getElementById("btnActualizar").addEventListener("click", cargarDatos);

// El filtro se aplica sobre los datos ya cargados, sin volver a consultar
document.getElementById("soloMedidos").addEventListener("change", () => {
  pintarTabla(kpisActuales);
});

document.getElementById("btnSalir").addEventListener("click", () => API.cerrarSesion());

document.getElementById("btnCerrarGrafico").addEventListener("click", () => {
  document.getElementById("seccionGrafico").classList.add("oculto");
});

document.querySelector("#tablaKpis tbody").addEventListener("click", (evento) => {
  const alerta = evento.target.closest("button[data-alerta]");
  if (alerta) {
    abrirModalAlerta(kpisActuales[Number(alerta.dataset.alerta)]);
    return;
  }

  const boton = evento.target.closest("button[data-indice]");
  if (boton) mostrarGrafico(kpisActuales[Number(boton.dataset.indice)]);
});

// El panel de alertas puede referirse a indicadores de otros procesos,
// por lo que se busca el detalle completo antes de abrir la ventana
document.getElementById("listaAlertas").addEventListener("click", async (evento) => {
  const boton = evento.target.closest("button[data-alerta-kpi]");
  if (!boton) return;

  const idKpi = Number(boton.dataset.alertaKpi);
  let indicador = kpisActuales.find((k) => k.id_kpi === idKpi);

  if (!indicador) {
    try {
      const todos = await API.kpis("general");
      indicador = todos.find((k) => k.id_kpi === idKpi);
    } catch {
      return;
    }
  }

  if (indicador) abrirModalAlerta(indicador);
});

/* ---------------- Ventana modal de notificación ---------------- */
document.getElementById("modalConfirmar").addEventListener("click", confirmarNotificacion);
document.getElementById("modalCancelar").addEventListener("click", cerrarModalAlerta);
document.getElementById("modalCerrar").addEventListener("click", cerrarModalAlerta);

// Cerrar al pulsar fuera de la ventana o con la tecla Escape
document.getElementById("modalAlerta").addEventListener("click", (evento) => {
  if (evento.target.id === "modalAlerta") cerrarModalAlerta();
});

/* ---------------- Incidencias técnicas (RF8) ---------------- */
document.getElementById("btnIncidencia").addEventListener("click", abrirModalIncidencia);
document.getElementById("incidenciaEnviar").addEventListener("click", enviarIncidencia);
document.getElementById("incidenciaCancelar").addEventListener("click", cerrarModalIncidencia);
document.getElementById("incidenciaCerrar").addEventListener("click", cerrarModalIncidencia);

document.getElementById("modalIncidencia").addEventListener("click", (evento) => {
  if (evento.target.id === "modalIncidencia") cerrarModalIncidencia();
});

document.addEventListener("keydown", (evento) => {
  if (evento.key !== "Escape") return;
  cerrarModalAlerta();
  cerrarModalIncidencia();
});

document.getElementById("btnExportar").addEventListener("click", async () => {
  try {
    await API.descargarCsv(document.getElementById("selectorProceso").value);
  } catch (error) {
    alert("No se pudo exportar: " + error.message);
  }
});

document.getElementById("btnReporte").addEventListener("click", async (evento) => {
  const boton = evento.currentTarget;
  const original = boton.textContent;

  boton.disabled = true;
  boton.textContent = "Generando…";

  try {
    await API.descargarPdf(document.getElementById("selectorProceso").value);
  } catch (error) {
    alert("No se pudo generar el reporte: " + error.message);
  } finally {
    boton.disabled = false;
    boton.textContent = original;
  }
});

document.getElementById("btnVerReporte").addEventListener("click", async () => {
  try {
    await API.abrirReporte(document.getElementById("selectorProceso").value);
  } catch (error) {
    alert("No se pudo abrir el reporte: " + error.message);
  }
});

/* ---------------- Carga de archivos CSV (RF1) ---------------- */
document.getElementById("formCarga").addEventListener("submit", async (evento) => {
  evento.preventDefault();

  const proceso = document.getElementById("procesoCarga").value;
  const entrada = document.getElementById("archivoCarga");
  const salida = document.getElementById("resultadoCarga");
  const boton = evento.target.querySelector("button");

  if (!entrada.files.length) {
    salida.innerHTML = '<div class="fallo">Seleccione un archivo CSV.</div>';
    return;
  }

  boton.disabled = true;
  boton.textContent = "Procesando…";
  salida.innerHTML = "";

  try {
    const r = await API.cargarArchivo(proceso, entrada.files[0]);

    const advertencias = r.advertencias.length
      ? `<ul>${r.advertencias.map((a) => `<li>${a}</li>`).join("")}</ul>`
      : "";

    salida.innerHTML = `
      <div class="exito">
        <strong>Carga completada.</strong>
        Se procesaron ${r.filas_leidas} filas y se registraron
        ${r.resultados_registrados} resultados
        (períodos: ${r.periodos_procesados.join(", ")}).
        ${advertencias}
      </div>`;

    entrada.value = "";
    await cargarDatos();
  } catch (error) {
    salida.innerHTML = `<div class="fallo"><strong>No se pudo procesar el archivo.</strong><br>${error.message}</div>`;
  } finally {
    boton.disabled = false;
    boton.textContent = "Procesar archivo";
  }
});

/* ------------------------------------------------------------
   Inicio
   ------------------------------------------------------------ */
prepararSesion();
cargarSelectorProcesos().then(cargarDatos);
