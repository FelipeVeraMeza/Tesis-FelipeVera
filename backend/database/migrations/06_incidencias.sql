-- ============================================================
-- Registro de incidencias tecnicas (RF8)
--
-- Permite a cualquier usuario del sistema reportar errores o
-- fallas detectadas durante su uso, dejando constancia del
-- modulo afectado y del contexto en que se produjo.
--
-- Es un registro de soporte del propio sistema, independiente de
-- la Gestion de Incidentes TI, que corresponde a un proceso del
-- negocio y se mide mediante sus propios indicadores.
-- ============================================================

CREATE TABLE IF NOT EXISTS incidencia (
    id_incidencia SERIAL PRIMARY KEY,
    id_usuario    INTEGER      REFERENCES usuario(id_usuario),

    modulo        VARCHAR(50)  NOT NULL,          -- Dashboard, Carga de datos, Reportes, Otro
    severidad     VARCHAR(20)  NOT NULL DEFAULT 'Media',   -- Alta | Media | Baja
    titulo        VARCHAR(150) NOT NULL,
    descripcion   VARCHAR(1000) NOT NULL,

    estado        VARCHAR(30)  NOT NULL DEFAULT 'Abierta', -- Abierta | En revision | Cerrada
    fecha_reporte TIMESTAMP    NOT NULL DEFAULT NOW(),
    fecha_cierre  TIMESTAMP,
    resolucion    VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS idx_incidencia_estado ON incidencia(estado);
CREATE INDEX IF NOT EXISTS idx_incidencia_fecha  ON incidencia(fecha_reporte DESC);

-- Misma proteccion que el resto del modelo (RNF3)
ALTER TABLE incidencia ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidencia FORCE  ROW LEVEL SECURITY;

REVOKE ALL ON incidencia FROM anon, authenticated;
