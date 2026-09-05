-- ============================================================
-- Ampliacion del catalogo
--
-- El levantamiento realizado en la Gerencia de TI identifico 21
-- procesos y 44 indicadores, de los cuales solo una parte resulto
-- viable de medir. Para representar esa realidad se incorporan
-- dos atributos al modelo:
--
--   proceso_ti.critico       marca los cuatro procesos definidos
--                            como criticos en el alcance
--   indicador_kpi.perspectiva clasificacion COBIT del indicador
--
-- El resto del modelo logico (Tablas 17 a 23) se mantiene sin
-- cambios.
-- ============================================================

ALTER TABLE proceso_ti
    ADD COLUMN IF NOT EXISTS critico BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE indicador_kpi
    ADD COLUMN IF NOT EXISTS perspectiva VARCHAR(100);

-- El catalogo ampliado admite procesos sin responsable asignado y
-- nombres de indicador repetidos entre procesos distintos.
ALTER TABLE proceso_ti    ALTER COLUMN responsable    DROP NOT NULL;
ALTER TABLE indicador_kpi ALTER COLUMN unidad_medida  DROP NOT NULL;

CREATE INDEX IF NOT EXISTS idx_proceso_critico ON proceso_ti(critico);
CREATE INDEX IF NOT EXISTS idx_kpi_viable      ON indicador_kpi(viable);
