-- ============================================================
-- Sistema de seguimiento y visualizacion de KPIs
-- AFP Horizonte - Gerencia de Tecnologias de la Informacion
-- Modelo logico (Tablas 17 a 23 de la memoria) - PostgreSQL
-- Normalizado hasta 3FN
-- ============================================================

DROP TABLE IF EXISTS resultado_kpi   CASCADE;
DROP TABLE IF EXISTS meta_kpi        CASCADE;
DROP TABLE IF EXISTS indicador_kpi   CASCADE;
DROP TABLE IF EXISTS fuente_dato     CASCADE;
DROP TABLE IF EXISTS proceso_ti      CASCADE;
DROP TABLE IF EXISTS usuario         CASCADE;
DROP TABLE IF EXISTS rol             CASCADE;

-- ------------------------------------------------------------
-- Tabla 17: ROL   (1 rol : N usuarios)
-- ------------------------------------------------------------
CREATE TABLE rol (
    id_rol       SERIAL PRIMARY KEY,
    nombre_rol   VARCHAR(50)  NOT NULL UNIQUE,
    descripcion  VARCHAR(150)
);

-- ------------------------------------------------------------
-- Tabla 18: USUARIO   (N usuarios : 1 rol)
-- ------------------------------------------------------------
CREATE TABLE usuario (
    id_usuario     SERIAL PRIMARY KEY,
    nombre_usuario VARCHAR(100) NOT NULL,
    correo         VARCHAR(100) NOT NULL UNIQUE,
    contrasena     VARCHAR(200) NOT NULL,          -- hash PBKDF2, nunca texto plano (RNF3)
    id_rol         INTEGER      NOT NULL REFERENCES rol(id_rol),
    activo         BOOLEAN      NOT NULL DEFAULT TRUE,
    fecha_creacion TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- Tabla 19: PROCESO_TI   (1 usuario : N procesos)
-- ------------------------------------------------------------
CREATE TABLE proceso_ti (
    id_proceso           SERIAL PRIMARY KEY,
    nombre_proceso       VARCHAR(150) NOT NULL,
    codigo_proceso       VARCHAR(30)  NOT NULL UNIQUE,   -- cambios | incidentes | requerimientos | demanda
    descripcion          VARCHAR(250),
    responsable          VARCHAR(100),
    estado               VARCHAR(50)  NOT NULL DEFAULT 'Activo',
    fecha_actualizacion  DATE         NOT NULL DEFAULT CURRENT_DATE,
    id_usuario           INTEGER      REFERENCES usuario(id_usuario)
);

-- ------------------------------------------------------------
-- Tabla 23: FUENTE_DATO   (1 fuente : N resultados)
-- ------------------------------------------------------------
CREATE TABLE fuente_dato (
    id_fuente     SERIAL PRIMARY KEY,
    nombre_fuente VARCHAR(100) NOT NULL,
    tipo_fuente   VARCHAR(50)  NOT NULL,      -- CSV, Excel, sistema externo
    descripcion   VARCHAR(200),
    fecha_carga   TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- Tabla 20: INDICADOR_KPI   (1 proceso : N KPIs)
-- ------------------------------------------------------------
CREATE TABLE indicador_kpi (
    id_kpi          SERIAL PRIMARY KEY,
    nombre_kpi      VARCHAR(150) NOT NULL,
    codigo_kpi      VARCHAR(50)  NOT NULL UNIQUE,   -- clave usada por el ETL
    descripcion     VARCHAR(350),
    formula         VARCHAR(350),
    unidad_medida   VARCHAR(50),                    -- %, dias, horas, cantidad
    periodicidad    VARCHAR(50)  DEFAULT 'Mensual',
    id_proceso      INTEGER      NOT NULL REFERENCES proceso_ti(id_proceso) ON DELETE CASCADE,
    valor_minimo    NUMERIC(10,2),
    valor_maximo    NUMERIC(10,2),
    meta            NUMERIC(10,2),
    tipo_medicion   SMALLINT     NOT NULL DEFAULT 1,   -- 1 = mayor es mejor, 2 = menor es mejor
    tipo_grafico    SMALLINT     NOT NULL DEFAULT 1,   -- 1 = barra, 2 = linea, 3 = torta
    estado          VARCHAR(30)  NOT NULL DEFAULT 'Activo',
    viable          VARCHAR(5)   DEFAULT 'Si',
    dueno_proceso   VARCHAR(100),
    prioridad_impl  SMALLINT,
    fuente_origen   VARCHAR(50),
    observaciones   VARCHAR(350)
);

-- ------------------------------------------------------------
-- Tabla 21: META_KPI   (1 KPI : 1 meta vigente)
-- ------------------------------------------------------------
CREATE TABLE meta_kpi (
    id_meta        SERIAL PRIMARY KEY,
    id_kpi         INTEGER NOT NULL REFERENCES indicador_kpi(id_kpi) ON DELETE CASCADE,
    valor_objetivo NUMERIC(10,2) NOT NULL,
    valor_minimo   NUMERIC(10,2),
    valor_maximo   NUMERIC(10,2),
    vigente        BOOLEAN NOT NULL DEFAULT TRUE
);

-- ------------------------------------------------------------
-- Tabla 22: RESULTADO_KPI   (1 KPI : N resultados)
-- ------------------------------------------------------------
CREATE TABLE resultado_kpi (
    id_resultado   SERIAL PRIMARY KEY,
    id_kpi         INTEGER NOT NULL REFERENCES indicador_kpi(id_kpi) ON DELETE CASCADE,
    valor_real     NUMERIC(10,2) NOT NULL,
    fecha_registro DATE    NOT NULL,
    periodo        VARCHAR(7) NOT NULL,               -- formato AAAA-MM
    id_fuente      INTEGER REFERENCES fuente_dato(id_fuente),
    CONSTRAINT uq_resultado_periodo UNIQUE (id_kpi, periodo)
);

-- ------------------------------------------------------------
-- Indices de apoyo a las consultas del dashboard (RNF1)
-- ------------------------------------------------------------
CREATE INDEX idx_kpi_proceso        ON indicador_kpi(id_proceso);
CREATE INDEX idx_resultado_kpi      ON resultado_kpi(id_kpi);
CREATE INDEX idx_resultado_periodo  ON resultado_kpi(periodo);
