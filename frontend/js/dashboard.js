/* ============================================================
   Panel de análisis del desempeño de procesos TI

   La aplicación se organiza en vistas que responden preguntas
   distintas —estado general, análisis por proceso, catálogo de
   indicadores, evolución histórica, alertas y reportes— y
   comparten un mismo conjunto de filtros, de modo que el
   contexto se conserva al cambiar de vista.
   ============================================================ */

const usuario = API.obtenerUsuario();
if (!API.obtenerToken() || !usuario) {
  window.location.replace("login.html");
}

const PERMISOS = usuario.permisos || {};
const PUEDE_NOTIFICAR = PERMISOS.puede_notificar === true;

const ETIQUETAS_ESTADO = {
  cumple: "Cumple",
  riesgo: "En riesgo",
  bajo: "Bajo desempeño",
  sin_datos: "Sin datos",
};

const COLORES = {
  azul: "#14446e",
  azulClaro: "#3282b8",
  verde: "#177243",
  ambar: "#8a5c0d",
  rojo: "#b93b3b",
  gris: "#5c6b7d",
};

/* Cada perfil accede a un enfoque distinto del panel (RF5) */
const VISTAS_PERFIL = {
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

const PERFIL = VISTAS_PERFIL[PERMISOS.vista] || VISTAS_PERFIL.detallada;

/* ------------------------------------------------------------
   Estado de la aplicación

   Se mantiene en un único lugar para que todas las vistas
   reflejen el mismo contexto de filtros.
   ------------------------------------------------------------ */
const estado = {
  vista: "resumen",
  filtros: {
    // Todos los perfiles parten del alcance declarado en el proyecto
    proceso: "criticos",
    estado: "todos",
    busqueda: "",
    severidad: "todas",
  },
  datos: {
    kpis: [],
    resumen: [],
    alertas: [],
    general: null,
    evolucion: [],
    procesos: [],
  },
  procesoAbierto: null,
  indicadorTendencia: null,
  kpiEnAlerta: null,
};

const graficos = { evolucion: null, tendencia: null };

/* ------------------------------------------------------------
   Utilidades
   ------------------------------------------------------------ */
const $ = (id) => document.getElementById(id);

function formatearValor(valor, unidad) {
  if (valor === null || valor === undefined) return "—";
  const numero = Number(valor);
  const texto = Number.isInteger(numero) ? numero.toString() : numero.toFixed(2);
  if (unidad === "%") return `${texto} %`;
  if (unidad === "cantidad" || !unidad) return texto;
  return `${texto} ${unidad}`;
}

function colorEstado(estadoKpi) {
  return (
    { cumple: COLORES.verde, riesgo: COLORES.ambar, bajo: COLORES.rojo }[estadoKpi] ||
    COLORES.gris
  );
}

function escaparHtml(texto) {
  const div = document.createElement("div");
  div.textContent = texto ?? "";
  return div.innerHTML;
}

function flechaTendencia(kpi) {
  return kpi.tendencia === "ascendente" ? "↑" : "↓";
}

const MESES = [
  "ene", "feb", "mar", "abr", "may", "jun",
  "jul", "ago", "sep", "oct", "nov", "dic",
];

/* ------------------------------------------------------------
   Degradado del área bajo la curva

   Un relleno que se desvanece hacia abajo aporta profundidad sin
   competir con la línea, que es lo que interesa leer.
   ------------------------------------------------------------ */
function degradado(lienzo, color) {
  const contexto = lienzo.getContext("2d");
  const alto = lienzo.height || 320;
  const franja = contexto.createLinearGradient(0, 0, 0, alto);

  const rgb = hexARgb(color);
  franja.addColorStop(0, `rgba(${rgb}, .16)`);
  franja.addColorStop(1, `rgba(${rgb}, .01)`);

  return franja;
}

function hexARgb(hex) {
  const limpio = hex.replace("#", "");
  const entero = parseInt(limpio, 16);
  return `${(entero >> 16) & 255}, ${(entero >> 8) & 255}, ${entero & 255}`;
}

/* Convierte "2025-03" en "mar 2025", más legible en tablas y ejes */
function formatearPeriodo(periodo) {
  const [anio, mes] = String(periodo).split("-");
  const indice = Number(mes) - 1;
  return MESES[indice] ? `${MESES[indice]} ${anio}` : periodo;
}

/* ------------------------------------------------------------
   Situación de un proceso

   Se determina por el estado de sus indicadores y no por el
   promedio de cumplimiento: una desviación pequeña en magnitud
   sigue siendo un incumplimiento.
   ------------------------------------------------------------ */
function situacionProceso(bloque) {
  if (bloque.kpis_medidos === 0) return "";

  const dentro = bloque.kpis_medidos - bloque.en_alerta;

  // Ningún indicador dentro de meta
  if (dentro === 0) return "bajo";

  // Todos dentro de meta
  if (bloque.en_alerta === 0) return "cumple";

  // Situación mixta: la mayoría dentro de meta se informa como riesgo;
  // por debajo de la mitad, como bajo desempeño
  return dentro / bloque.kpis_medidos >= 0.5 ? "riesgo" : "bajo";
}

/* Aplica los filtros globales sobre la lista de indicadores */
function kpisFiltrados() {
  const { estado: filtroEstado, busqueda } = estado.filtros;
  const texto = busqueda.trim().toLowerCase();

  return estado.datos.kpis.filter((kpi) => {
    if (filtroEstado !== "todos" && kpi.estado !== filtroEstado) return false;
    if (!texto) return true;
    return (
      kpi.nombre.toLowerCase().includes(texto) ||
      (kpi.proceso_nombre || "").toLowerCase().includes(texto)
    );
  });
}

/* ------------------------------------------------------------
   Navegación entre vistas
   ------------------------------------------------------------ */
function irA(vista, opciones = {}) {
  estado.vista = vista;

  document.querySelectorAll(".pestana").forEach((boton) => {
    boton.classList.toggle("activa", boton.dataset.vista === vista);
  });

  document.querySelectorAll(".vista").forEach((seccion) => {
    seccion.classList.toggle("activa", seccion.id === `vista-${vista}`);
  });

  // Cada vista se dibuja al mostrarse, para reflejar los filtros vigentes
  const pintar = {
    resumen: pintarResumen,
    procesos: pintarProcesos,
    indicadores: pintarIndicadores,
    tendencias: pintarTendencias,
    alertas: pintarAlertas,
    reportes: pintarReportes,
  }[vista];

  if (pintar) pintar(opciones);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ------------------------------------------------------------
   Carga de datos
   ------------------------------------------------------------ */
async function cargarDatos() {
  const proceso = estado.filtros.proceso;

  try {
    const [kpis, resumen, alertas, general, evolucion] = await Promise.all([
      API.kpis(proceso),
      API.resumen(),
      API.alertas(proceso),
      API.estadoGeneral(proceso),
      API.evolucion(proceso),
    ]);

    Object.assign(estado.datos, { kpis, resumen, alertas, general, evolucion });

    actualizarContadorAlertas();
    actualizarContexto();
    irA(estado.vista);
  } catch (error) {
    $("tarjetasSintesis").innerHTML =
      `<p class="estado-carga">No se pudieron obtener los datos: ${escaparHtml(error.message)}</p>`;
  }
}

function actualizarContadorAlertas() {
  const total = estado.datos.alertas.length;

  for (const id of ["contadorAlertas", "pestanaAlertasBadge"]) {
    const elemento = $(id);
    elemento.textContent = total;
    elemento.classList.toggle("oculto", total === 0);
  }
}

function actualizarContexto() {
  const selector = $("filtroProceso");
  const nombre = selector.options[selector.selectedIndex]?.textContent || "";

  // El catálogo completo corresponde al levantamiento de la Gerencia y
  // excede los cuatro procesos definidos en el alcance del proyecto
  const nota = $("notaAlcance");
  if (nota) {
    nota.classList.toggle("oculto", estado.filtros.proceso !== "general");
  }
  const { estado: filtroEstado, busqueda } = estado.filtros;

  const partes = [nombre];
  if (filtroEstado !== "todos") partes.push(ETIQUETAS_ESTADO[filtroEstado]);
  if (busqueda.trim()) partes.push(`«${busqueda.trim()}»`);

  $("contextoFiltro").textContent = partes.join(" · ");
}

/* ============================================================
   VISTA · RESUMEN
   ============================================================ */
function pintarResumen() {
  const g = estado.datos.general;
  if (!g) return;

  $("tituloVista").textContent = PERFIL.titulo;
  $("descripcionVista").textContent = PERFIL.descripcion;
  $("nivelVista").textContent = `Nivel ${PERFIL.nivel}`;

  pintarSintesis(g);
  pintarAtencion();
  pintarEvolucion();
  pintarBarrasProcesos();
}

function pintarSintesis(g) {
  const variacion =
    g.variacion === null || g.variacion === undefined
      ? '<span class="sintesis-nota">sin período previo</span>'
      : `<span class="sintesis-nota ${g.variacion >= 0 ? "positiva" : "negativa"}">
           ${g.variacion >= 0 ? "▲" : "▼"} ${Math.abs(g.variacion)} pp respecto al período anterior
         </span>`;

  const claseGlobal =
    g.cumplimiento_global === null
      ? ""
      : g.cumplimiento_global >= 90
      ? "cumple"
      : g.cumplimiento_global >= 75
      ? "riesgo"
      : "bajo";

  $("tarjetasSintesis").innerHTML = `
    <article class="tarjeta-sintesis ${claseGlobal}">
      <span class="sintesis-rotulo">Cumplimiento global</span>
      <span class="sintesis-cifra">${g.cumplimiento_global !== null ? g.cumplimiento_global + " %" : "—"}</span>
      ${variacion}
    </article>

    <article class="tarjeta-sintesis">
      <span class="sintesis-rotulo">Indicadores</span>
      <span class="sintesis-cifra">${g.indicadores_cumplen}<small>/${g.indicadores_medidos}</small></span>
      <span class="sintesis-nota">cumplen su meta · ${g.indicadores_totales} definidos</span>
    </article>

    <article class="tarjeta-sintesis">
      <span class="sintesis-rotulo">Procesos</span>
      <span class="sintesis-cifra">${g.procesos_en_meta}<small>/${g.procesos_medidos ?? g.procesos_totales}</small></span>
      <span class="sintesis-nota">dentro de meta${
        g.procesos_medidos !== undefined && g.procesos_medidos < g.procesos_totales
          ? ` · ${g.procesos_totales - g.procesos_medidos} sin mediciones`
          : ""
      }</span>
    </article>

    <article class="tarjeta-sintesis ${g.indicadores_desviados ? "bajo" : ""}">
      <span class="sintesis-rotulo">Requieren atención</span>
      <span class="sintesis-cifra">${g.indicadores_desviados}</span>
      <span class="sintesis-nota">${g.indicadores_criticos} en estado crítico</span>
    </article>

    <article class="tarjeta-sintesis">
      <span class="sintesis-rotulo">Último período</span>
      <span class="sintesis-cifra periodo">${g.periodo_actual ? formatearPeriodo(g.periodo_actual) : "—"}</span>
      <span class="sintesis-nota">${g.periodos.length} períodos registrados</span>
    </article>`;
}

function pintarAtencion() {
  const bloque = $("bloqueAtencion");
  const criticas = estado.datos.alertas.filter((a) => a.estado === "bajo").slice(0, 4);

  if (!criticas.length) {
    bloque.classList.add("oculto");
    return;
  }

  $("listaAtencion").innerHTML = criticas
    .map((a) => {
      const brecha =
        a.meta !== null && a.valor !== null
          ? `${(a.valor - a.meta).toFixed(1)} ${a.unidad === "%" ? "pp" : ""}`
          : "—";

      return `
        <article class="fila-atencion">
          <span class="marca-severidad ${a.estado}"></span>
          <div class="atencion-texto">
            <strong>${escaparHtml(a.kpi)}</strong>
            <span>${escaparHtml(a.proceso)}</span>
          </div>
          <div class="atencion-cifras">
            <span class="valor-actual">${formatearValor(a.valor, a.unidad)}</span>
            <span class="valor-meta">meta ${formatearValor(a.meta, a.unidad)}</span>
          </div>
          <span class="atencion-brecha">${brecha}</span>
          <button class="btn-secundario" data-analizar="${a.id_kpi}">Analizar</button>
        </article>`;
    })
    .join("");

  bloque.classList.remove("oculto");
}

function pintarEvolucion() {
  const serie = estado.datos.evolucion;
  const lienzo = $("graficoEvolucion");

  if (graficos.evolucion) graficos.evolucion.destroy();
  if (!serie.length) return;

  graficos.evolucion = new Chart(lienzo.getContext("2d"), {
    type: "line",
    data: {
      labels: serie.map((p) => formatearPeriodo(p.periodo)),
      datasets: [
        {
          label: "Cumplimiento promedio",
          data: serie.map((p) => p.cumplimiento),
          borderColor: COLORES.azul,
          backgroundColor: degradado(lienzo, COLORES.azul),
          borderWidth: 2,
          tension: 0.28,
          fill: true,
          pointBackgroundColor: "#fff",
          pointBorderColor: COLORES.azul,
          pointBorderWidth: 2,
          pointRadius: serie.length > 14 ? 0 : 3.5,
          pointHoverRadius: 6,
        },
        {
          label: "Margen sobre la meta",
          data: serie.map((p) => p.holgura),
          borderColor: COLORES.verde,
          borderWidth: 1.8,
          borderDash: [5, 4],
          tension: 0.28,
          fill: false,
          pointBackgroundColor: "#fff",
          pointBorderColor: COLORES.verde,
          pointBorderWidth: 2,
          pointRadius: serie.length > 14 ? 0 : 3,
          pointHoverRadius: 5,
        },
      ],
    },
    options: opcionesGrafico(
      "%",
      rangoSerie([
        ...serie.map((p) => p.cumplimiento),
        ...serie.map((p) => p.holgura),
      ])
    ),
  });
}

/* ------------------------------------------------------------
   Rango del eje vertical

   Partir siempre en cero aplana las series concentradas en un
   tramo estrecho. El eje se ajusta a los valores observados,
   dejando un margen para que la línea no toque los bordes.
   ------------------------------------------------------------ */
function rangoSerie(valores, referencia = null) {
  const puntos = valores.filter((v) => v !== null && v !== undefined);
  if (!puntos.length) return {};

  if (referencia !== null) puntos.push(referencia);

  const menor = Math.min(...puntos);
  const mayor = Math.max(...puntos);
  const amplitud = mayor - menor;

  // Con valores casi idénticos se abre una ventana mínima legible
  const margen = amplitud < 1 ? Math.max(Math.abs(mayor) * 0.05, 1) : amplitud * 0.15;

  return {
    minimo: Math.max(0, Math.floor(menor - margen)),
    maximo: Math.ceil(mayor + margen),
  };
}

function pintarBarrasProcesos() {
  const contenedor = $("barrasProcesos");
  let procesos = estado.datos.resumen;

  if (estado.filtros.proceso === "criticos") {
    procesos = procesos.filter((p) => p.critico);
  } else if (estado.filtros.proceso !== "general") {
    procesos = procesos.filter((p) => p.proceso === estado.filtros.proceso);
  }

  const conDatos = procesos.filter((p) => p.cumplimiento_promedio !== null);

  if (!conDatos.length) {
    contenedor.innerHTML = '<p class="estado-carga">Sin mediciones para el filtro actual.</p>';
    return;
  }

  contenedor.innerHTML = conDatos
    .sort((a, b) => a.cumplimiento_promedio - b.cumplimiento_promedio)
    .map((p) => {
      const valor = p.cumplimiento_promedio;
      const clase = situacionProceso(p);

      return `
        <div class="barra-proceso" data-proceso="${p.proceso}" role="button" tabindex="0">
          <div class="barra-cabecera">
            <span class="barra-nombre">${escaparHtml(p.nombre)}</span>
            <span class="barra-valor ${clase}">${valor} %</span>
          </div>
          <div class="barra-pista">
            <div class="barra-relleno ${clase}" style="width:${Math.min(valor, 100)}%"></div>
          </div>
          <span class="barra-nota">
            ${p.kpis_medidos - p.en_alerta} de ${p.kpis_medidos} indicadores dentro de meta${
              p.en_alerta ? ` · ${p.en_alerta} en alerta` : ""
            }
          </span>
        </div>`;
    })
    .join("");
}

/* ============================================================
   VISTA · PROCESOS
   ============================================================ */
function pintarProcesos() {
  const contenedor = $("tarjetasProcesos");
  let procesos = estado.datos.resumen;

  if (estado.filtros.proceso === "criticos") {
    procesos = procesos.filter((p) => p.critico);
  } else if (estado.filtros.proceso !== "general") {
    procesos = procesos.filter((p) => p.proceso === estado.filtros.proceso);
  }

  // El filtro de estado deja los procesos que tienen algún indicador
  // en la situación seleccionada
  const filtroEstado = estado.filtros.estado;
  if (filtroEstado !== "todos") {
    const conEseEstado = new Set(
      estado.datos.kpis.filter((k) => k.estado === filtroEstado).map((k) => k.proceso)
    );
    procesos = procesos.filter((p) => conEseEstado.has(p.proceso));
  }

  // La búsqueda acota a los procesos cuyo nombre coincide
  const texto = estado.filtros.busqueda.trim().toLowerCase();
  if (texto) {
    procesos = procesos.filter((p) => (p.nombre || "").toLowerCase().includes(texto));
  }

  if (!procesos.length) {
    contenedor.innerHTML =
      '<p class="estado-carga">Ningún proceso coincide con los filtros aplicados.</p>';
    return;
  }

  contenedor.innerHTML = procesos
    .map((p) => {
      const valor = p.cumplimiento_promedio;
      const clase = situacionProceso(p);

      const dentro = p.kpis_medidos - p.en_alerta;
      const nota =
        p.kpis_medidos === 0
          ? `Sin mediciones · ${p.total_kpis} indicadores definidos`
          : p.en_alerta > 0
          ? `${dentro} de ${p.kpis_medidos} dentro de meta · ${p.en_alerta} requiere${
              p.en_alerta > 1 ? "n" : ""
            } atención`
          : `${p.kpis_medidos} de ${p.kpis_medidos} indicadores dentro de meta`;

      const dentroDeMeta = p.kpis_medidos - p.en_alerta;
      const proporcion = p.kpis_medidos ? (dentroDeMeta / p.kpis_medidos) * 100 : 0;

      return `
        <article class="tarjeta ${clase}" data-proceso="${p.proceso}" role="button" tabindex="0">
          <h3>${escaparHtml(p.nombre)}${p.critico ? '<span class="insignia tenue">Crítico</span>' : ""}</h3>

          ${
            p.kpis_medidos
              ? `<p class="tarjeta-valor">${dentroDeMeta}<small>/${p.kpis_medidos}</small></p>
                 <span class="tarjeta-unidad">indicadores dentro de meta</span>
                 <div class="barra-pista compacta">
                   <div class="barra-relleno ${clase}" style="width:${proporcion}%"></div>
                 </div>
                 <span class="tarjeta-detalle">
                   ${valor !== null ? `Cumplimiento promedio ${valor} %` : ""}
                 </span>`
              : `<p class="tarjeta-valor sin-medir">—</p>
                 <span class="tarjeta-unidad">sin mediciones</span>
                 <span class="tarjeta-detalle">${p.total_kpis} indicadores definidos</span>`
          }

          ${
            p.kpis_medidos && p.kpis_medidos < p.total_kpis
              ? `<span class="tarjeta-cobertura">${p.kpis_medidos} de ${p.total_kpis} con medición</span>`
              : ""
          }
        </article>`;
    })
    .join("");

  if (estado.procesoAbierto) abrirProceso(estado.procesoAbierto);
}

async function abrirProceso(codigo) {
  estado.procesoAbierto = codigo;

  const bloque = estado.datos.resumen.find((p) => p.proceso === codigo);
  if (!bloque) return;

  $("tituloDetalleProceso").textContent = bloque.nombre;

  let indicadores = estado.datos.kpis.filter((k) => k.proceso === codigo);

  // Si el filtro global no incluye este proceso, se consultan sus indicadores
  if (!indicadores.length) {
    try {
      indicadores = await API.kpis(codigo);
    } catch {
      indicadores = [];
    }
  }

  const cuerpo = document.querySelector("#tablaProceso tbody");

  cuerpo.innerHTML = indicadores.length
    ? indicadores
        .map(
          (k) => `
          <tr>
            <td class="celda-indicador"><strong>${escaparHtml(k.nombre)}</strong></td>
            <td class="valor-numerico">${formatearValor(k.valor, k.unidad)}</td>
            <td class="valor-numerico">${formatearValor(k.meta, k.unidad)}</td>
            <td class="celda-tendencia">${flechaTendencia(k)} ${k.tendencia}</td>
            <td><span class="estado ${k.estado}">${ETIQUETAS_ESTADO[k.estado]}</span></td>
            <td><button class="btn-secundario" data-detalle="${k.id_kpi}">Detalle</button></td>
          </tr>`
        )
        .join("")
    : '<tr><td colspan="6" class="estado-carga">Sin indicadores registrados.</td></tr>';

  $("detalleProceso").classList.remove("oculto");
  $("detalleProceso").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* ============================================================
   VISTA · INDICADORES
   ============================================================ */
function pintarIndicadores() {
  const cuerpo = document.querySelector("#tablaKpis tbody");
  const visibles = kpisFiltrados();
  const medidos = estado.datos.kpis.filter((k) => k.estado !== "sin_datos").length;

  $("contadorKpis").textContent =
    `${visibles.length} de ${estado.datos.kpis.length} indicadores · ${medidos} con medición`;

  if (!visibles.length) {
    cuerpo.innerHTML =
      '<tr><td colspan="8" class="estado-carga">Ningún indicador coincide con los filtros.</td></tr>';
    return;
  }

  cuerpo.innerHTML = visibles
    .map((kpi) => {
      const implementado =
        (kpi.estado_implementacion || "").toLowerCase() === "implementado";

      const marca = implementado
        ? ""
        : `<span class="insignia tenue">${kpi.viable === "Si" ? "Pendiente" : "No viable"}</span>`;

      const desviado = kpi.estado === "riesgo" || kpi.estado === "bajo";
      const alerta =
        desviado && PUEDE_NOTIFICAR
          ? `<button class="btn-sirena ${kpi.estado === "bajo" ? "severa" : ""}"
                     data-alerta="${kpi.id_kpi}" title="Notificar al responsable">🚨</button>`
          : "";

      const proyeccion = kpi.analisis
        ? `${formatearValor(kpi.proyeccion, kpi.unidad)}
           <small class="confianza ${kpi.analisis.confiabilidad}">R²=${kpi.analisis.r2}</small>`
        : "—";

      return `
        <tr>
          <td class="celda-indicador">
            <strong>${escaparHtml(kpi.nombre)}</strong>
            ${marca}
          </td>
          <td><span class="insignia">${escaparHtml(kpi.proceso_nombre || "—")}</span></td>
          <td class="valor-numerico">${formatearValor(kpi.valor, kpi.unidad)}</td>
          <td class="valor-numerico">${formatearValor(kpi.meta, kpi.unidad)}</td>
          <td class="celda-tendencia">${flechaTendencia(kpi)}</td>
          <td><span class="estado ${kpi.estado}">${ETIQUETAS_ESTADO[kpi.estado]}</span></td>
          <td class="valor-numerico">${proyeccion}</td>
          <td class="celda-acciones">
            ${alerta}
            <button class="btn-secundario" data-detalle="${kpi.id_kpi}">Detalle</button>
          </td>
        </tr>`;
    })
    .join("");
}

/* ============================================================
   VISTA · TENDENCIAS
   ============================================================ */
function pintarTendencias(opciones = {}) {
  const selector = $("selectorIndicador");
  const conSerie = estado.datos.kpis.filter((k) => k.historico.length > 0);

  if (!conSerie.length) {
    selector.innerHTML = '<option value="">Sin indicadores con mediciones</option>';
    $("resumenTendencia").innerHTML = "";
    $("fichaIndicador").innerHTML =
      '<p class="estado-carga">No hay series históricas para el filtro actual.</p>';
    if (graficos.tendencia) graficos.tendencia.destroy();
    document.querySelector("#tablaMediciones tbody").innerHTML = "";
    return;
  }

  selector.innerHTML = conSerie
    .map((k) => `<option value="${k.id_kpi}">${escaparHtml(k.nombre)}</option>`)
    .join("");

  const idSolicitado = opciones.idKpi || estado.indicadorTendencia;
  const elegido =
    conSerie.find((k) => k.id_kpi === Number(idSolicitado)) || conSerie[0];

  selector.value = elegido.id_kpi;
  mostrarTendencia(elegido);
}

function mostrarTendencia(kpi) {
  estado.indicadorTendencia = kpi.id_kpi;

  const a = kpi.analisis;
  $("resumenTendencia").innerHTML = a
    ? `
      <div class="dato-tendencia">
        <span>Dirección</span><strong>${a.direccion}</strong>
      </div>
      <div class="dato-tendencia">
        <span>Variación por período</span>
        <strong>${a.pendiente > 0 ? "+" : ""}${a.pendiente}</strong>
      </div>
      <div class="dato-tendencia">
        <span>Ajuste (R²)</span>
        <strong class="confianza ${a.confiabilidad}">${a.r2} · ${a.confiabilidad}</strong>
      </div>
      <div class="dato-tendencia">
        <span>Períodos</span><strong>${a.periodos}</strong>
      </div>`
    : '<p class="ayuda">La serie no tiene períodos suficientes para estimar una tendencia.</p>';

  dibujarGraficoTendencia(kpi);

  $("fichaIndicador").innerHTML = `
    <dl class="ficha">
      <div><dt>Proceso</dt><dd>${escaparHtml(kpi.proceso_nombre || "—")}</dd></div>
      <div><dt>Fórmula</dt><dd>${escaparHtml(kpi.formula || "—")}</dd></div>
      <div><dt>Unidad</dt><dd>${escaparHtml(kpi.unidad || "—")}</dd></div>
      <div><dt>Periodicidad</dt><dd>${escaparHtml(kpi.periodicidad || "—")}</dd></div>
      <div><dt>Responsable</dt><dd>${escaparHtml(kpi.dueno_proceso || "—")}</dd></div>
      <div><dt>Fuente</dt><dd>${escaparHtml(kpi.fuente_origen || "—")}</dd></div>
    </dl>`;

  const cuerpo = document.querySelector("#tablaMediciones tbody");
  cuerpo.innerHTML = [...kpi.historico]
    .reverse()
    .map((punto) => {
      const est = evaluarPunto(punto.valor, kpi.meta, kpi.tipo_medicion);
      return `
        <tr>
          <td class="celda-periodo">${formatearPeriodo(punto.periodo)}</td>
          <td class="valor-numerico">${formatearValor(punto.valor, kpi.unidad)}</td>
          <td class="valor-numerico">${formatearValor(kpi.meta, kpi.unidad)}</td>
          <td><span class="estado ${est}">${ETIQUETAS_ESTADO[est]}</span></td>
        </tr>`;
    })
    .join("");
}

/* Réplica de la clasificación del servidor, para la tabla de mediciones */
function evaluarPunto(valor, meta, tipoMedicion) {
  if (valor === null || meta === null) return "sin_datos";
  if (tipoMedicion === 2) {
    if (valor <= meta) return "cumple";
    return meta && valor <= meta * 1.2 ? "riesgo" : "bajo";
  }
  if (valor >= meta) return "cumple";
  return meta && valor >= meta * 0.8 ? "riesgo" : "bajo";
}

function dibujarGraficoTendencia(kpi) {
  const lienzo = $("graficoTendencia");
  if (graficos.tendencia) graficos.tendencia.destroy();

  const etiquetas = kpi.historico.map((p) => formatearPeriodo(p.periodo));
  const valores = kpi.historico.map((p) => p.valor);
  const conProyeccion = kpi.proyeccion !== null && kpi.proyeccion !== undefined;

  const color = colorEstado(kpi.estado);

  const conjuntos = [
    {
      label: "Valor medido",
      data: valores,
      borderColor: color,
      backgroundColor: degradado(lienzo, color),
      borderWidth: 2,
      tension: 0.25,
      fill: valores.length > 1,
      pointBackgroundColor: "#fff",
      pointBorderColor: color,
      pointBorderWidth: 2,
      // Con series extensas los puntos se muestran solo al posarse encima
      pointRadius: valores.length > 14 ? 0 : 3.5,
      pointHoverRadius: 6,
      pointHoverBorderWidth: 2.5,
    },
  ];

  if (conProyeccion && valores.length > 1) {
    conjuntos.push({
      label: "Proyección",
      data: [...Array(valores.length - 1).fill(null), valores.at(-1), kpi.proyeccion],
      borderColor: COLORES.azulClaro,
      borderDash: [4, 4],
      borderWidth: 2,
      pointRadius: 5,
      pointStyle: "triangle",
      pointBackgroundColor: COLORES.azulClaro,
      pointBorderColor: "#fff",
      pointBorderWidth: 1.5,
      fill: false,
    });
  }

  graficos.tendencia = new Chart(lienzo.getContext("2d"), {
    // Una sola medición se representa como barra: no hay evolución que trazar
    type: valores.length === 1 ? "bar" : "line",
    data: {
      labels: conProyeccion && valores.length > 1 ? [...etiquetas, "Proyectado"] : etiquetas,
      datasets: conjuntos,
    },
    options: {
      ...opcionesGrafico(kpi.unidad, {
        ...rangoSerie([...valores, kpi.proyeccion], kpi.meta),
        meta: kpi.meta,
      }),
      plugins: {
        ...opcionesGrafico(kpi.unidad, { meta: kpi.meta }).plugins,
        bandaMeta: { meta: kpi.meta, tendencia: kpi.tendencia },
      },
    },
  });
}

/* ============================================================
   Configuración común de los gráficos

   El criterio de presentación sigue el de un reporte de gestión:
   la grilla se mantiene tenue, la meta se marca como referencia y
   el detalle se reserva para la información emergente.
   ============================================================ */
const FUENTE = { family: "Inter, system-ui, sans-serif" };

const EJE = {
  tick: { ...FUENTE, size: 11 },
  color: "#5c6b7d",
  grilla: "#eef2f6",
  borde: "#dde5ec",
};

function opcionesGrafico(unidad, extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    layout: { padding: { top: 12, right: 12, bottom: 4 } },

    plugins: {
      legend: {
        position: "bottom",
        align: "start",
        labels: {
          usePointStyle: true,
          pointStyle: "line",
          boxWidth: 22,
          boxHeight: 2,
          padding: 18,
          font: { ...FUENTE, size: 11.5 },
          color: "#46586b",
        },
      },
      tooltip: {
        backgroundColor: "#0a2540",
        titleColor: "#ffffff",
        titleFont: { ...FUENTE, size: 12, weight: "600" },
        bodyColor: "#dce6f0",
        bodyFont: { ...FUENTE, size: 12 },
        padding: { top: 10, bottom: 10, left: 12, right: 14 },
        cornerRadius: 6,
        displayColors: true,
        boxWidth: 8,
        boxHeight: 8,
        boxPadding: 5,
        borderColor: "rgba(255,255,255,.12)",
        borderWidth: 1,
        callbacks: {
          label: (ctx) => ` ${ctx.dataset.label}: ${formatearValor(ctx.parsed.y, unidad)}`,
          // La distancia respecto a la meta se informa junto al valor
          afterBody: (items) => {
            if (extra.meta === undefined || extra.meta === null) return "";
            const punto = items.find((i) => i.datasetIndex === 0);
            if (!punto) return "";

            const diferencia = punto.parsed.y - extra.meta;
            const signo = diferencia >= 0 ? "+" : "";
            return `\nRespecto a la meta: ${signo}${diferencia.toFixed(2)}`;
          },
        },
      },
    },

    scales: {
      x: {
        grid: { display: false },
        border: { color: EJE.borde },
        ticks: {
          font: EJE.tick,
          color: EJE.color,
          maxRotation: 0,
          autoSkipPadding: 16,
        },
      },
      y: {
        beginAtZero: extra.minimo === undefined,
        min: extra.minimo,
        max: extra.maximo,
        grid: { color: EJE.grilla, drawTicks: false },
        border: { display: false },
        ticks: {
          font: EJE.tick,
          color: EJE.color,
          padding: 12,
          maxTicksLimit: 7,
          callback: (valor) => formatearValor(valor, unidad),
        },
      },
    },

    elements: {
      line: { borderCapStyle: "round", borderJoinStyle: "round" },
      point: { hitRadius: 12 },
    },
  };
}

/* ------------------------------------------------------------
   Banda de meta

   Sombrea la zona favorable del gráfico, de modo que el
   cumplimiento se aprecie sin necesidad de leer los valores.
   ------------------------------------------------------------ */
const bandaMeta = {
  id: "bandaMeta",
  beforeDatasetsDraw(grafico, _args, opciones) {
    const { meta, tendencia } = opciones || {};
    if (meta === undefined || meta === null) return;

    const { ctx, chartArea, scales } = grafico;
    if (!chartArea || !scales.y) return;

    const y = scales.y.getPixelForValue(meta);
    if (!Number.isFinite(y)) return;

    const desdeArriba = tendencia === "ascendente";
    const inicio = desdeArriba ? chartArea.top : y;
    const alto = desdeArriba ? y - chartArea.top : chartArea.bottom - y;

    if (alto <= 0) return;

    ctx.save();
    ctx.fillStyle = "rgba(23, 114, 67, .045)";
    ctx.fillRect(chartArea.left, inicio, chartArea.right - chartArea.left, alto);

    // Línea de referencia sobre el valor de la meta
    ctx.strokeStyle = "rgba(138, 92, 13, .5)";
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 4]);
    ctx.beginPath();
    ctx.moveTo(chartArea.left, y);
    ctx.lineTo(chartArea.right, y);
    ctx.stroke();
    ctx.restore();
  },
};

if (typeof Chart !== "undefined") {
  Chart.register(bandaMeta);
  Chart.defaults.font.family = FUENTE.family;
  Chart.defaults.color = "#46586b";
}

/* ============================================================
   VISTA · ALERTAS
   ============================================================ */
function pintarAlertas() {
  const contenedor = $("listaAlertas");
  const severidad = estado.filtros.severidad;

  let alertas = estado.datos.alertas;
  if (severidad !== "todas") {
    alertas = alertas.filter((a) => a.estado === severidad);
  }

  if (!alertas.length) {
    contenedor.innerHTML =
      '<p class="estado-carga">No hay alertas para el criterio seleccionado.</p>';
    return;
  }

  contenedor.innerHTML = alertas
    .map((a) => {
      const brecha =
        a.brecha !== null && a.brecha !== undefined
          ? `${a.brecha > 0 ? "+" : ""}${a.brecha}${a.unidad === "%" ? " pp" : ""}`
          : "—";

      const tendencia = a.direccion
        ? `${a.direccion}${a.confiabilidad ? ` · ajuste ${a.confiabilidad}` : ""}`
        : "serie insuficiente";

      return `
        <article class="tarjeta-alerta ${a.estado}">
          <header class="alerta-cabecera">
            <span class="estado ${a.estado}">${ETIQUETAS_ESTADO[a.estado]}</span>
            ${a.critico ? '<span class="insignia">Proceso crítico</span>' : ""}
          </header>

          <h3>${escaparHtml(a.kpi)}</h3>
          <p class="alerta-proceso">${escaparHtml(a.proceso)}</p>

          <dl class="alerta-datos">
            <div><dt>Resultado</dt><dd>${formatearValor(a.valor, a.unidad)}</dd></div>
            <div><dt>Meta</dt><dd>${formatearValor(a.meta, a.unidad)}</dd></div>
            <div><dt>Brecha</dt><dd class="brecha">${brecha}</dd></div>
            <div><dt>Tendencia</dt><dd>${tendencia}</dd></div>
            <div><dt>Períodos medidos</dt><dd>${a.periodos ?? "—"}</dd></div>
            <div><dt>Responsable</dt><dd>${escaparHtml(a.dueno_proceso || "—")}</dd></div>
          </dl>

          <footer class="alerta-acciones">
            <button class="btn-secundario" data-analizar="${a.id_kpi}">Analizar</button>
            ${
              PUEDE_NOTIFICAR
                ? `<button class="btn-primario" data-alerta="${a.id_kpi}">Notificar</button>`
                : ""
            }
          </footer>
        </article>`;
    })
    .join("");
}

/* ============================================================
   VISTA · REPORTES
   ============================================================ */
async function pintarReportes() {
  if (PERMISOS.puede_cargar) $("seccionCarga").classList.remove("oculto");

  const cuerpo = document.querySelector("#tablaCargas tbody");

  try {
    const cargas = await API.cargas();

    cuerpo.innerHTML = cargas.length
      ? cargas
          .slice(0, 25)
          .map(
            (c) => `
            <tr>
              <td>${escaparHtml(c.archivo || "—")}</td>
              <td>${escaparHtml(c.proceso || "—")}</td>
              <td><span class="insignia">${escaparHtml(c.tipo || "—")}</span></td>
              <td class="valor-numerico">${c.filas ?? "—"}</td>
              <td class="celda-periodos">${escaparHtml(c.periodos || "—")}</td>
              <td>${escaparHtml(c.responsable || "—")}</td>
              <td>${(c.fecha || "").replace("T", " ").slice(0, 16)}</td>
            </tr>`
          )
          .join("")
      : '<tr><td colspan="7" class="estado-carga">Sin cargas registradas.</td></tr>';
  } catch {
    cuerpo.innerHTML =
      '<tr><td colspan="7" class="estado-carga">No se pudo obtener el historial.</td></tr>';
  }
}

/* ============================================================
   Detalle del indicador
   ============================================================ */
function abrirDetalleIndicador(idKpi) {
  const kpi = estado.datos.kpis.find((k) => k.id_kpi === Number(idKpi));
  if (!kpi) return;

  estado.indicadorTendencia = kpi.id_kpi;
  $("indicadorTitulo").textContent = kpi.nombre;

  const a = kpi.analisis;

  $("indicadorCuerpo").innerHTML = `
    <div class="detalle-cabecera">
      <div class="detalle-valor ${kpi.estado}">
        <span class="detalle-cifra">${formatearValor(kpi.valor, kpi.unidad)}</span>
        <span class="detalle-meta">meta ${formatearValor(kpi.meta, kpi.unidad)}</span>
      </div>
      <span class="estado ${kpi.estado}">${ETIQUETAS_ESTADO[kpi.estado]}</span>
    </div>

    <dl class="ficha">
      <div><dt>Proceso</dt><dd>${escaparHtml(kpi.proceso_nombre || "—")}</dd></div>
      <div><dt>Fórmula</dt><dd>${escaparHtml(kpi.formula || "—")}</dd></div>
      <div><dt>Tendencia esperada</dt><dd>${kpi.tendencia}</dd></div>
      <div><dt>Periodicidad</dt><dd>${escaparHtml(kpi.periodicidad || "—")}</dd></div>
      <div><dt>Fuente</dt><dd>${escaparHtml(kpi.fuente_origen || "—")}</dd></div>
      <div><dt>Responsable</dt><dd>${escaparHtml(kpi.dueno_proceso || "—")}</dd></div>
      <div><dt>Estado de implementación</dt><dd>${escaparHtml(kpi.estado_implementacion || "—")}</dd></div>
      <div><dt>Mediciones</dt><dd>${kpi.historico.length}</dd></div>
      ${
        a
          ? `<div><dt>Proyección</dt><dd>${formatearValor(kpi.proyeccion, kpi.unidad)} · R²=${a.r2} (${a.confiabilidad})</dd></div>`
          : ""
      }
    </dl>`;

  $("modalIndicador").classList.remove("oculto");
}

/* ============================================================
   Notificación de desviaciones (RF7)
   ============================================================ */
function abrirModalAlerta(idKpi) {
  const kpi = estado.datos.kpis.find((k) => k.id_kpi === Number(idKpi));
  if (!kpi) return;

  estado.kpiEnAlerta = kpi;

  $("alertaKpi").textContent = kpi.nombre;
  $("alertaProceso").textContent = kpi.proceso_nombre || "—";
  $("alertaValor").textContent = formatearValor(kpi.valor, kpi.unidad);
  $("alertaMeta").textContent = formatearValor(kpi.meta, kpi.unidad);
  $("alertaDestinatario").textContent =
    kpi.dueno_proceso || kpi.proceso_nombre || "Gerencia de TI";
  $("alertaEstado").innerHTML =
    `<span class="estado ${kpi.estado}">${ETIQUETAS_ESTADO[kpi.estado]}</span>`;

  $("modalConfirmacion").classList.remove("oculto");
  $("modalResultado").classList.add("oculto");
  $("modalError").textContent = "";

  const confirmar = $("modalConfirmar");
  confirmar.classList.remove("oculto");
  confirmar.disabled = false;
  confirmar.textContent = "Enviar notificación";
  $("modalCancelar").textContent = "Cancelar";

  $("modalAlerta").classList.remove("oculto");
  confirmar.focus();
}

async function confirmarNotificacion() {
  const kpi = estado.kpiEnAlerta;
  if (!kpi) return;

  const boton = $("modalConfirmar");
  boton.disabled = true;
  boton.textContent = "Enviando…";
  $("modalError").textContent = "";

  try {
    const respuesta = await API.notificar(kpi.id_kpi);

    $("resultadoDetalle").textContent =
      `Se notificó a ${respuesta.destinatario} sobre la desviación del indicador ` +
      `«${respuesta.kpi}»` +
      (respuesta.simulada
        ? ". El envío por correo se encuentra simulado en esta etapa."
        : ".");

    $("resultadoMensaje").textContent = respuesta.mensaje;
    $("modalConfirmacion").classList.add("oculto");
    $("modalResultado").classList.remove("oculto");
    boton.classList.add("oculto");
    $("modalCancelar").textContent = "Cerrar";
  } catch (error) {
    $("modalError").textContent = error.message;
    boton.disabled = false;
    boton.textContent = "Enviar notificación";
  }
}

/* ============================================================
   Incidencias técnicas (RF8)
   ============================================================ */
function abrirModalIncidencia() {
  $("incidenciaFormulario").classList.remove("oculto");
  $("incidenciaResultado").classList.add("oculto");
  $("incidenciaError").textContent = "";
  $("incidenciaTituloCampo").value = "";
  $("incidenciaDescripcion").value = "";

  const enviar = $("incidenciaEnviar");
  enviar.classList.remove("oculto");
  enviar.disabled = false;
  enviar.textContent = "Registrar";
  $("incidenciaCancelar").textContent = "Cancelar";

  $("modalIncidencia").classList.remove("oculto");
  $("incidenciaTituloCampo").focus();
}

async function enviarIncidencia() {
  const enviar = $("incidenciaEnviar");
  const datos = {
    modulo: $("incidenciaModulo").value,
    severidad: $("incidenciaSeveridad").value,
    titulo: $("incidenciaTituloCampo").value.trim(),
    descripcion: $("incidenciaDescripcion").value.trim(),
  };

  if (datos.titulo.length < 5) {
    $("incidenciaError").textContent = "Indique un título de al menos 5 caracteres.";
    return;
  }
  if (datos.descripcion.length < 10) {
    $("incidenciaError").textContent = "Describa la incidencia con al menos 10 caracteres.";
    return;
  }

  enviar.disabled = true;
  enviar.textContent = "Registrando…";
  $("incidenciaError").textContent = "";

  try {
    const r = await API.registrarIncidencia(datos);
    $("incidenciaDetalle").textContent =
      `La incidencia N.º ${r.id_incidencia} quedó registrada en estado ${r.estado}.`;
    $("incidenciaFormulario").classList.add("oculto");
    $("incidenciaResultado").classList.remove("oculto");
    enviar.classList.add("oculto");
    $("incidenciaCancelar").textContent = "Cerrar";
  } catch (error) {
    $("incidenciaError").textContent = error.message;
    enviar.disabled = false;
    enviar.textContent = "Registrar";
  }
}

/* ============================================================
   Exportación
   ============================================================ */
async function exportar(tipo) {
  const proceso = estado.filtros.proceso;
  $("menuExportar").classList.add("oculto");

  try {
    if (tipo === "csv") await API.descargarCsv(proceso);
    else if (tipo === "pdf") await API.descargarPdf(proceso);
    else await API.abrirReporte(proceso);
  } catch (error) {
    alert("No se pudo generar el documento: " + error.message);
  }
}

/* ============================================================
   Inicialización de controles
   ============================================================ */
async function cargarSelectorProcesos() {
  const selector = $("filtroProceso");

  try {
    const procesos = await API.procesos();
    estado.datos.procesos = procesos;

    const criticos = procesos.filter((p) => p.critico);
    const resto = procesos.filter((p) => !p.critico);

    const opciones = (lista) =>
      lista
        .map((p) => `<option value="${p.codigo_proceso}">${escaparHtml(p.nombre_proceso)}</option>`)
        .join("");

    selector.innerHTML =
      '<option value="criticos">Procesos críticos · alcance del proyecto</option>' +
      '<option value="general">Catálogo completo de la Gerencia</option>' +
      (criticos.length ? `<optgroup label="Críticos">${opciones(criticos)}</optgroup>` : "") +
      (resto.length ? `<optgroup label="Otros procesos">${opciones(resto)}</optgroup>` : "");

    selector.value = estado.filtros.proceso;
  } catch {
    // El selector conserva la opción por defecto
  }
}

function registrarEventos() {
  /* --- Pestañas --- */
  document.querySelectorAll(".pestana").forEach((boton) => {
    boton.addEventListener("click", () => irA(boton.dataset.vista));
  });

  /* --- Filtros globales --- */
  $("filtroProceso").addEventListener("change", (e) => {
    estado.filtros.proceso = e.target.value;
    estado.procesoAbierto = null;
    $("detalleProceso").classList.add("oculto");
    cargarDatos();
  });

  $("filtroEstado").addEventListener("change", (e) => {
    estado.filtros.estado = e.target.value;
    actualizarContexto();
    irA(estado.vista);
  });

  let temporizador;
  $("filtroBusqueda").addEventListener("input", (e) => {
    estado.filtros.busqueda = e.target.value;
    clearTimeout(temporizador);
    temporizador = setTimeout(() => {
      actualizarContexto();
      if (estado.vista === "indicadores") pintarIndicadores();
      else irA("indicadores");
    }, 300);
  });

  $("btnLimpiar").addEventListener("click", () => {
    estado.filtros.estado = "todos";
    estado.filtros.busqueda = "";
    estado.filtros.severidad = "todas";
    $("filtroEstado").value = "todos";
    $("filtroBusqueda").value = "";
    document.querySelectorAll(".chip").forEach((c) =>
      c.classList.toggle("activo", c.dataset.severidad === "todas")
    );
    actualizarContexto();
    irA(estado.vista);
  });

  $("btnActualizar").addEventListener("click", cargarDatos);

  /* --- Menús desplegables --- */
  const alternar = (menu) => {
    document.querySelectorAll(".menu-desplegable").forEach((m) => {
      if (m !== menu) m.classList.add("oculto");
    });
    menu.classList.toggle("oculto");
  };

  $("btnExportarMenu").addEventListener("click", (e) => {
    e.stopPropagation();
    alternar($("menuExportar"));
  });

  $("btnUsuario").addEventListener("click", (e) => {
    e.stopPropagation();
    alternar($("menuUsuario"));
  });

  document.addEventListener("click", () => {
    document.querySelectorAll(".menu-desplegable").forEach((m) => m.classList.add("oculto"));
  });

  document.querySelectorAll("[data-exportar]").forEach((boton) => {
    boton.addEventListener("click", () => exportar(boton.dataset.exportar));
  });

  /* --- Accesos directos entre vistas --- */
  $("btnAlertas").addEventListener("click", () => irA("alertas"));

  document.querySelectorAll("[data-ir]").forEach((boton) => {
    boton.addEventListener("click", () => irA(boton.dataset.ir));
  });

  /* --- Chips de severidad --- */
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      estado.filtros.severidad = chip.dataset.severidad;
      document.querySelectorAll(".chip").forEach((c) => c.classList.remove("activo"));
      chip.classList.add("activo");
      pintarAlertas();
    });
  });

  /* --- Interacción con el contenido (drill-down) --- */
  document.addEventListener("click", (evento) => {
    const analizar = evento.target.closest("[data-analizar]");
    if (analizar) {
      irA("tendencias", { idKpi: analizar.dataset.analizar });
      return;
    }

    const detalle = evento.target.closest("[data-detalle]");
    if (detalle) {
      abrirDetalleIndicador(detalle.dataset.detalle);
      return;
    }

    const alerta = evento.target.closest("[data-alerta]");
    if (alerta) {
      abrirModalAlerta(alerta.dataset.alerta);
      return;
    }

    const proceso = evento.target.closest("[data-proceso]");
    if (proceso) {
      if (estado.vista === "resumen") {
        irA("procesos");
        setTimeout(() => abrirProceso(proceso.dataset.proceso), 120);
      } else {
        abrirProceso(proceso.dataset.proceso);
      }
    }
  });

  // Las tarjetas de proceso son operables con teclado
  document.addEventListener("keydown", (evento) => {
    if (evento.key !== "Enter" && evento.key !== " ") return;
    const proceso = evento.target.closest?.("[data-proceso]");
    if (proceso) {
      evento.preventDefault();
      proceso.click();
    }
  });

  $("cerrarDetalleProceso").addEventListener("click", () => {
    estado.procesoAbierto = null;
    $("detalleProceso").classList.add("oculto");
  });

  /* --- Tendencias --- */
  $("selectorIndicador").addEventListener("change", (e) => {
    const kpi = estado.datos.kpis.find((k) => k.id_kpi === Number(e.target.value));
    if (kpi) mostrarTendencia(kpi);
  });

  /* --- Modales --- */
  $("modalConfirmar").addEventListener("click", confirmarNotificacion);
  $("modalCancelar").addEventListener("click", () => $("modalAlerta").classList.add("oculto"));
  $("modalCerrar").addEventListener("click", () => $("modalAlerta").classList.add("oculto"));

  $("btnIncidencia").addEventListener("click", abrirModalIncidencia);
  $("incidenciaEnviar").addEventListener("click", enviarIncidencia);
  $("incidenciaCancelar").addEventListener("click", () =>
    $("modalIncidencia").classList.add("oculto")
  );
  $("incidenciaCerrar").addEventListener("click", () =>
    $("modalIncidencia").classList.add("oculto")
  );

  $("indicadorCerrar").addEventListener("click", () =>
    $("modalIndicador").classList.add("oculto")
  );
  $("indicadorCerrarPie").addEventListener("click", () =>
    $("modalIndicador").classList.add("oculto")
  );
  $("indicadorVerTendencia").addEventListener("click", () => {
    $("modalIndicador").classList.add("oculto");
    irA("tendencias", { idKpi: estado.indicadorTendencia });
  });

  document.querySelectorAll(".modal-fondo").forEach((fondo) => {
    fondo.addEventListener("click", (e) => {
      if (e.target === fondo) fondo.classList.add("oculto");
    });
  });

  document.addEventListener("keydown", (evento) => {
    if (evento.key !== "Escape") return;
    document.querySelectorAll(".modal-fondo").forEach((m) => m.classList.add("oculto"));
    document.querySelectorAll(".menu-desplegable").forEach((m) => m.classList.add("oculto"));
  });

  $("btnSalir").addEventListener("click", () => API.cerrarSesion());

  /* --- Carga de archivos (RF1) --- */
  $("formCarga").addEventListener("submit", async (evento) => {
    evento.preventDefault();

    const entrada = $("archivoCarga");
    const salida = $("resultadoCarga");
    const boton = evento.target.querySelector("button");

    if (!entrada.files.length) {
      salida.innerHTML = '<div class="fallo">Seleccione un archivo.</div>';
      return;
    }

    boton.disabled = true;
    boton.textContent = "Procesando…";
    salida.innerHTML = "";

    try {
      const r = await API.cargarArchivo($("procesoCarga").value, entrada.files[0]);

      const advertencias = r.advertencias.length
        ? `<ul>${r.advertencias.map((a) => `<li>${escaparHtml(a)}</li>`).join("")}</ul>`
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
      pintarReportes();
    } catch (error) {
      salida.innerHTML =
        `<div class="fallo"><strong>No se pudo procesar el archivo.</strong><br>${escaparHtml(error.message)}</div>`;
    } finally {
      boton.disabled = false;
      boton.textContent = "Procesar";
    }
  });
}

/* ------------------------------------------------------------
   Inicio
   ------------------------------------------------------------ */
function prepararSesion() {
  $("usuarioNombre").textContent = usuario.nombre;
  $("usuarioNombreMenu").textContent = usuario.nombre;
  $("usuarioRol").textContent = usuario.rol;

  if (!PERMISOS.puede_exportar) {
    $("btnExportarMenu").classList.add("oculto");
  }
}

prepararSesion();
registrarEventos();
cargarSelectorProcesos().then(cargarDatos);
