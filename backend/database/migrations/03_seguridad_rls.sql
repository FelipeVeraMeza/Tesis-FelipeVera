-- ============================================================
-- Seguridad: Row Level Security (RLS)
-- Sistema de seguimiento de KPIs - AFP Horizonte
--
-- Cumple el requisito no funcional RNF3 (seguridad de la
-- informacion y control de acceso).
--
-- CRITERIO APLICADO
-- -----------------
-- La arquitectura del sistema es de cuatro capas: el navegador
-- nunca consulta la base de datos directamente, sino que lo hace
-- a traves de la API REST desarrollada en Flask. Esa capa de
-- aplicacion es la unica que se conecta a la base, y lo hace con
-- la clave de servicio (service role), que por diseno no esta
-- sujeta a las politicas de RLS.
--
-- En consecuencia, la configuracion correcta es habilitar RLS en
-- todas las tablas y NO definir politicas de acceso publico: se
-- cierra por completo el acceso anonimo, mientras el backend
-- mantiene su operacion normal.
--
-- El control de acceso por perfil (Gerente, Lider, Analista,
-- Administrador) se resuelve en la capa de aplicacion, en el
-- modulo backend/app/auth.py.
-- ============================================================

-- ------------------------------------------------------------
-- 1. Habilitar RLS en las siete tablas del modelo
-- ------------------------------------------------------------
ALTER TABLE public.rol           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usuario       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.proceso_ti    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fuente_dato   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.indicador_kpi ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.meta_kpi      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.resultado_kpi ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------
-- 2. Forzar RLS tambien para el propietario de las tablas
-- ------------------------------------------------------------
ALTER TABLE public.rol           FORCE ROW LEVEL SECURITY;
ALTER TABLE public.usuario       FORCE ROW LEVEL SECURITY;
ALTER TABLE public.proceso_ti    FORCE ROW LEVEL SECURITY;
ALTER TABLE public.fuente_dato   FORCE ROW LEVEL SECURITY;
ALTER TABLE public.indicador_kpi FORCE ROW LEVEL SECURITY;
ALTER TABLE public.meta_kpi      FORCE ROW LEVEL SECURITY;
ALTER TABLE public.resultado_kpi FORCE ROW LEVEL SECURITY;

-- ------------------------------------------------------------
-- 3. Eliminar cualquier politica previa
--    Sin politicas definidas, RLS deniega todo acceso a los
--    roles anonimo y autenticado.
-- ------------------------------------------------------------
DO $$
DECLARE
    politica RECORD;
BEGIN
    FOR politica IN
        SELECT policyname, tablename
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename IN ('rol', 'usuario', 'proceso_ti', 'fuente_dato',
                            'indicador_kpi', 'meta_kpi', 'resultado_kpi')
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I',
                       politica.policyname, politica.tablename);
    END LOOP;
END $$;

-- ------------------------------------------------------------
-- 4. Revocar privilegios de los roles publicos
--    Segunda barrera, independiente de RLS: aunque en el futuro
--    se agregara una politica por error, estos roles no tienen
--    permiso para operar sobre las tablas.
-- ------------------------------------------------------------
REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;

-- Que las tablas creadas a futuro tampoco queden expuestas
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM anon, authenticated;

-- ------------------------------------------------------------
-- 5. Verificacion
-- ------------------------------------------------------------
SELECT
    tablename                        AS tabla,
    rowsecurity                      AS rls_habilitado,
    (SELECT COUNT(*)
       FROM pg_policies p
      WHERE p.schemaname = 'public'
        AND p.tablename = t.tablename) AS politicas
FROM pg_tables t
WHERE schemaname = 'public'
  AND tablename IN ('rol', 'usuario', 'proceso_ti', 'fuente_dato',
                    'indicador_kpi', 'meta_kpi', 'resultado_kpi')
ORDER BY tablename;
