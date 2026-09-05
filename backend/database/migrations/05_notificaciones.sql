-- ============================================================
-- Modulo de alertas y notificaciones (RF7)
--
-- Registra las notificaciones que el Gerente o el Lider de TI
-- emiten hacia el responsable de un proceso cuando un indicador
-- presenta desviaciones respecto a su meta.
--
-- En esta etapa de prototipo el envio es simulado: la
-- notificacion queda registrada en la base de datos y se muestra
-- en la interfaz. La estructura contempla los campos necesarios
-- para integrar un servidor de correo SMTP en una fase futura,
-- sin modificar el modelo.
-- ============================================================

CREATE TABLE IF NOT EXISTS notificacion (
    id_notificacion  SERIAL PRIMARY KEY,
    id_kpi           INTEGER      NOT NULL REFERENCES indicador_kpi(id_kpi) ON DELETE CASCADE,
    id_usuario       INTEGER      REFERENCES usuario(id_usuario),

    -- Estado del indicador al momento de emitir la alerta
    estado_kpi       VARCHAR(20)  NOT NULL,          -- riesgo | bajo
    valor_registrado NUMERIC(10,2),
    meta_referencia  NUMERIC(10,2),

    -- Destinatario y contenido
    destinatario     VARCHAR(150) NOT NULL,          -- dueno del proceso
    asunto           VARCHAR(200) NOT NULL,
    mensaje          VARCHAR(1000),

    -- Trazabilidad del envio
    canal            VARCHAR(30)  NOT NULL DEFAULT 'Simulado',  -- Simulado | Correo
    estado_envio     VARCHAR(30)  NOT NULL DEFAULT 'Registrada',
    fecha_envio      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notificacion_kpi   ON notificacion(id_kpi);
CREATE INDEX IF NOT EXISTS idx_notificacion_fecha ON notificacion(fecha_envio DESC);

-- Misma proteccion que el resto del modelo (RNF3)
ALTER TABLE notificacion ENABLE  ROW LEVEL SECURITY;
ALTER TABLE notificacion FORCE   ROW LEVEL SECURITY;

REVOKE ALL ON notificacion FROM anon, authenticated;
