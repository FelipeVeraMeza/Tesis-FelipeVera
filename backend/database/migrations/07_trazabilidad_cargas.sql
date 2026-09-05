-- ============================================================
-- Trazabilidad de las cargas de datos
--
-- El diseno del modulo de gestion de datos establece que cada
-- carga debe generar metadatos asociados: el usuario responsable,
-- la fecha de registro y la procedencia del archivo, de modo que
-- exista un historial de actualizaciones y trazabilidad completa
-- de los cambios realizados sobre la informacion.
--
-- Estos atributos se incorporan a la tabla fuente_dato, que ya
-- registra el origen de cada resultado.
-- ============================================================

ALTER TABLE fuente_dato
    ADD COLUMN IF NOT EXISTS id_usuario INTEGER REFERENCES usuario(id_usuario);

ALTER TABLE fuente_dato
    ADD COLUMN IF NOT EXISTS proceso VARCHAR(50);

ALTER TABLE fuente_dato
    ADD COLUMN IF NOT EXISTS filas_procesadas INTEGER;

ALTER TABLE fuente_dato
    ADD COLUMN IF NOT EXISTS periodos_cargados VARCHAR(200);

ALTER TABLE fuente_dato
    ADD COLUMN IF NOT EXISTS advertencias INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_fuente_usuario ON fuente_dato(id_usuario);
CREATE INDEX IF NOT EXISTS idx_fuente_fecha   ON fuente_dato(fecha_carga DESC);
