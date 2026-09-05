-- ============================================================
-- Datos iniciales (semilla)
-- Roles, usuarios, procesos criticos y fichas tecnicas de KPI
-- Fuente: Tablas 11 a 14 de la memoria de titulo
-- ============================================================

-- ---------------- ROLES (modulo de autenticacion y control de acceso) ----------------
INSERT INTO rol (nombre_rol, descripcion) VALUES
 ('Gerente',      'Vista ejecutiva consolidada de todos los procesos de TI'),
 ('Lider',        'Dashboards de cumplimiento y tendencias de sus procesos'),
 ('Analista',     'Carga de archivos CSV, validacion de datos y revision de KPI'),
 ('Administrador','Gestion tecnica del sistema y de la base de datos');

-- ---------------- USUARIOS ----------------
-- El hash de contrasena lo inyecta el script de inicializacion (RNF3).
INSERT INTO usuario (nombre_usuario, correo, contrasena, id_rol) VALUES
 ('Gerente de TI',       'gerente@horizonte.cl',  '__HASH__', (SELECT id_rol FROM rol WHERE nombre_rol='Gerente')),
 ('Lider de Proceso',    'lider@horizonte.cl',    '__HASH__', (SELECT id_rol FROM rol WHERE nombre_rol='Lider')),
 ('Analista de Proceso', 'analista@horizonte.cl', '__HASH__', (SELECT id_rol FROM rol WHERE nombre_rol='Analista')),
 ('Administrador TI',    'admin@horizonte.cl',    '__HASH__', (SELECT id_rol FROM rol WHERE nombre_rol='Administrador'));

-- ---------------- PROCESOS CRITICOS (los 4 del alcance) ----------------
INSERT INTO proceso_ti (nombre_proceso, codigo_proceso, descripcion, responsable, estado, id_usuario) VALUES
 ('Gestion de Cambios TI',        'cambios',        'Control de solicitudes de cambio sobre los servicios de TI',             'Lider de Cambios',        'Activo', 2),
 ('Gestion de Incidentes',        'incidentes',     'Restauracion de servicios afectados por interrupciones no planificadas', 'Lider de Incidentes',     'Activo', 2),
 ('Gestion de Requerimientos TI', 'requerimientos', 'Atencion de solicitudes de servicio de los usuarios internos',           'Lider de Requerimientos', 'Activo', 2),
 ('Gestion de Demanda TI',        'demanda',        'Recepcion, evaluacion y priorizacion de iniciativas tecnologicas',       'Subgerente Desarrollo TI','Activo', 2);

-- ---------------- FUENTES DE DATOS (Tabla 23) ----------------
INSERT INTO fuente_dato (nombre_fuente, tipo_fuente, descripcion) VALUES
 ('Carga manual CSV',   'CSV',   'Archivo plano cargado por el responsable de proceso'),
 ('Carga manual Excel', 'Excel', 'Planilla de calculo cargada por el analista'),
 ('Carga inicial',      'CSV',   'Datos historicos de referencia del prototipo');

-- ============================================================
-- INDICADOR_KPI (Tabla 20) - fichas tecnicas
-- tipo_medicion: 1 = ascendente (mayor es mejor) | 2 = descendente (menor es mejor)
-- tipo_grafico : 1 = barra | 2 = linea | 3 = torta
-- ============================================================

-- ---------- Tabla 11: Gestion de Cambios ----------
INSERT INTO indicador_kpi
 (nombre_kpi, codigo_kpi, descripcion, formula, unidad_medida, periodicidad, id_proceso,
  valor_minimo, valor_maximo, meta, tipo_medicion, tipo_grafico, dueno_proceso, prioridad_impl, fuente_origen)
VALUES
 ('Tasa de aceptacion de cambios', 'cam_tasa_aceptacion',
  'Porcentaje de solicitudes de cambio aceptadas respecto al total ingresado.',
  '(Cambios aceptados / Cambios solicitados) * 100', '%', 'Mensual',
  (SELECT id_proceso FROM proceso_ti WHERE codigo_proceso='cambios'), 0, 100, 90, 1, 1, 'Lider de Cambios', 1, 'CSV'),

 ('Cambios urgentes sobre el total', 'cam_urgentes',
  'Porcentaje de cambios urgentes ejecutados en el periodo.',
  '(Cambios urgentes / Total de cambios) * 100', '%', 'Mensual',
  (SELECT id_proceso FROM proceso_ti WHERE codigo_proceso='cambios'), 0, 100, 10, 2, 1, 'Lider de Cambios', 2, 'CSV'),

 ('Cambios con vuelta atras', 'cam_vuelta_atras',
  'Porcentaje de cambios revertidos tras su implementacion.',
  '(Cambios revertidos / Cambios implementados) * 100', '%', 'Mensual',
  (SELECT id_proceso FROM proceso_ti WHERE codigo_proceso='cambios'), 0, 100, 5, 2, 1, 'Lider de Cambios', 2, 'CSV'),

 ('Cambios con error en certificacion', 'cam_error_certificacion',
  'Porcentaje de cambios que presentaron errores durante la fase de certificacion.',
  '(Cambios con error en certificacion / Cambios implementados) * 100', '%', 'Mensual',
  (SELECT id_proceso FROM proceso_ti WHERE codigo_proceso='cambios'), 0, 100, 5, 2, 1, 'Lider de Cambios', 3, 'CSV');

-- ---------- Tabla 12: Gestion de Requerimientos ----------
INSERT INTO indicador_kpi
 (nombre_kpi, codigo_kpi, descripcion, formula, unidad_medida, periodicidad, id_proceso,
  valor_minimo, valor_maximo, meta, tipo_medicion, tipo_grafico, dueno_proceso, prioridad_impl, fuente_origen)
VALUES
 ('Cantidad de requerimientos rechazados', 'req_rechazados',
  'Numero total de requerimientos rechazados en el periodo.',
  'Sumatoria de requerimientos rechazados', 'cantidad', 'Mensual',
  (SELECT id_proceso FROM proceso_ti WHERE codigo_proceso='requerimientos'), 0, 500, 10, 2, 1, 'Lider de Requerimientos', 2, 'CSV'),

 ('Tiempo medio de resolucion', 'req_tiempo_medio',
  'Tiempo promedio en que se resuelven los requerimientos.',
  '(Sumatoria de tiempos de resolucion / Requerimientos cerrados)', 'dias', 'Mensual',
  (SELECT id_proceso FROM proceso_ti WHERE codigo_proceso='requerimientos'), 0, 60, 4, 2, 2, 'Lider de Requerimientos', 1, 'CSV'),

 ('Porcentaje de resolucion dentro de SLA', 'req_sla',
  'Proporcion de requerimientos resueltos dentro del tiempo comprometido.',
  '(Requerimientos dentro de SLA / Total de requerimientos cerrados) * 100', '%', 'Mensual',
  (SELECT id_proceso FROM proceso_ti WHERE codigo_proceso='requerimientos'), 0, 100, 85, 1, 1, 'Lider de Requerimientos', 1, 'CSV');

-- ---------- Tabla 13: Gestion de Incidentes ----------
INSERT INTO indicador_kpi
 (nombre_kpi, codigo_kpi, descripcion, formula, unidad_medida, periodicidad, id_proceso,
  valor_minimo, valor_maximo, meta, tipo_medicion, tipo_grafico, dueno_proceso, prioridad_impl, fuente_origen)
VALUES
 ('Tiempo de resolucion de incidente', 'inc_tiempo_resolucion',
  'Tiempo promedio para restaurar un servicio afectado.',
  '(Sumatoria de tiempos de resolucion / Incidentes cerrados en el periodo)', 'horas', 'Mensual',
  (SELECT id_proceso FROM proceso_ti WHERE codigo_proceso='incidentes'), 0, 72, 5, 2, 2, 'Lider de Incidentes', 1, 'CSV'),

 ('Capacidad de cierre de incidentes', 'inc_capacidad_cierre',
  'Porcentaje de incidentes cerrados respecto al total de incidentes generados.',
  '(Incidentes cerrados / Incidentes creados en el periodo) * 100', '%', 'Mensual',
  (SELECT id_proceso FROM proceso_ti WHERE codigo_proceso='incidentes'), 0, 100, 90, 1, 1, 'Lider de Incidentes', 1, 'CSV');

-- ---------- Tabla 14: Gestion de Demanda ----------
INSERT INTO indicador_kpi
 (nombre_kpi, codigo_kpi, descripcion, formula, unidad_medida, periodicidad, id_proceso,
  valor_minimo, valor_maximo, meta, tipo_medicion, tipo_grafico, dueno_proceso, prioridad_impl, fuente_origen)
VALUES
 ('Tiempo de ciclo de gestion de demanda', 'dem_tiempo_ciclo',
  'Tiempo promedio desde la recepcion de la solicitud hasta su priorizacion o rechazo.',
  '(Sumatoria de tiempos de priorizacion o rechazo / Total de solicitudes en el periodo)', 'dias', 'Mensual',
  (SELECT id_proceso FROM proceso_ti WHERE codigo_proceso='demanda'), 0, 90, 15, 2, 2, 'Subgerente Desarrollo TI', 2, 'CSV'),

 ('Porcentaje de solicitudes evaluadas dentro de SLA', 'dem_sla_evaluacion',
  'Proporcion de solicitudes priorizadas o rechazadas dentro del plazo comprometido.',
  '(Solicitudes evaluadas dentro de SLA / Total de solicitudes del periodo) * 100', '%', 'Mensual',
  (SELECT id_proceso FROM proceso_ti WHERE codigo_proceso='demanda'), 0, 100, 90, 1, 1, 'Subgerente Desarrollo TI', 1, 'CSV');

-- ---------------- META_KPI (Tabla 21) ----------------
INSERT INTO meta_kpi (id_kpi, valor_objetivo, valor_minimo, valor_maximo)
SELECT id_kpi, meta, valor_minimo, valor_maximo FROM indicador_kpi;
