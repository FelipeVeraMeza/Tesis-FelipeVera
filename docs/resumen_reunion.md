# Resumen para reunión de avance

**Proyecto de título · Felipe Vera Meza**
Desarrollo de un sistema de visualización de KPIs para la Gerencia de
Tecnologías de la Información · AFP Horizonte

---

# Parte 1 · Resumen de la memoria

## Problema

La Gerencia de TI de una administradora de fondos de pensiones consolidaba sus
indicadores de desempeño de forma manual: cada responsable descargaba archivos
desde distintas plataformas, los depuraba en planillas, aplicaba las fórmulas y
armaba gráficos que se consolidaban en un informe mensual.

Ese procedimiento presentaba tres problemas:

- Consumía tiempo y era propenso a errores en la manipulación.
- No dejaba trazabilidad: no quedaba registro de quién cargó qué dato ni cuándo.
- La información llegaba con hasta 30 días de desfase, lo que derivaba en
  decisiones reactivas.

## Objetivo

Desarrollar un sistema semi-automatizado de seguimiento y visualización de los
indicadores clave de desempeño de los procesos de TI, para optimizar la
eficiencia operativa y fortalecer la toma de decisiones.

**Objetivos específicos**

1. Sistematizar los indicadores necesarios para medir el desempeño.
2. Modelar el mapa de procesos y los flujos de información.
3. Desarrollar los procesos de carga, transformación y almacenamiento (ETL).
4. Implementar los dashboards de visualización.
5. Validar el modelo mediante juicio de expertos y escenarios simulados.

## Alcance

Cuatro procesos críticos, seleccionados por su impacto en la continuidad
operativa:

| Proceso | Indicadores | Ficha técnica |
|---|---:|---|
| Gestión de Cambios TI | 4 | Tabla 11 |
| Gestión de Requerimientos TI | 3 | Tabla 12 |
| Gestión de Incidentes TI | 2 | Tabla 13 |
| Gestión de la Demanda TI | 2 | Tabla 14 |
| **Total** | **11** | |

**Fuera del alcance:** despliegue productivo, procesos adicionales a los cuatro
críticos, conexión directa a sistemas transaccionales, mantenimiento posterior
al cierre y algoritmos de Machine Learning.

## Metodología

Enfoque aplicado, con diseño descriptivo y no experimental. Se adoptó una
adaptación del ciclo de vida dimensional de Kimball y Ross (2013), organizado
en fases: levantamiento, modelado, ETL, visualización y validación.

## Arquitectura

Cuatro capas con interfaces definidas:

| Capa | Tecnología |
|---|---|
| Presentación | HTML, CSS, JavaScript · Chart.js |
| Aplicación | Python · Flask (API REST) |
| Procesamiento | ETL · pandas · NumPy |
| Almacenamiento | Base de datos relacional · 7 tablas · 3FN |

El modelo lógico comprende las entidades Rol, Usuario, Proceso_TI,
Indicador_KPI, Meta_KPI, Resultado_KPI y Fuente_Dato (Tablas 17 a 23),
normalizadas hasta tercera forma normal.

## Requisitos

**Funcionales (Tabla 15):** RF1 carga de archivos · RF2 validación automática ·
RF3 procesamiento de indicadores · RF4 usuarios y autenticación ·
RF5 dashboards personalizados · RF6 reportes y exportación · RF7 alertas
automáticas · RF8 registro de incidencias · RF9 seguimiento histórico ·
RF10 módulo predictivo básico.

**No funcionales (Tabla 16):** RNF1 rendimiento bajo 10 segundos ·
RNF2 disponibilidad · RNF3 seguridad · RNF4 escalabilidad · RNF5 usabilidad ·
RNF6 mantenibilidad.

## Conclusiones de la memoria

El proyecto sistematizó los indicadores críticos, implementó el procesamiento
ETL y construyó un dashboard ejecutivo con semáforos, gráficos de tendencia y
alertas ante bajo desempeño, transformando una gestión reactiva en una
proactiva.

---

# Parte 2 · Estado del sistema

## Requisitos funcionales

| Requisito | Estado | Cómo se implementó |
|---|---|---|
| RF1 Carga de archivos | Cumplido | Admite CSV y Excel, con validación previa |
| RF2 Validación automática | Cumplido | Columnas, períodos, tipos, duplicados y coherencia |
| RF3 Procesamiento de indicadores | Cumplido | Las 11 fórmulas de las Tablas 11 a 14 |
| RF4 Usuarios y autenticación | Cumplido | Cuatro perfiles · PBKDF2-SHA256 · tokens firmados |
| RF5 Dashboards personalizados | Cumplido | Cuatro vistas según perfil, con nivel estratégico o táctico |
| RF6 Reportes y exportación | Cumplido | CSV y PDF descargable |
| RF7 Alertas automáticas | Cumplido | Detección, notificación al responsable y envío por correo |
| RF8 Registro de incidencias | Cumplido | Formulario y registro con trazabilidad |
| RF9 Seguimiento histórico | Cumplido | 25 períodos por indicador |
| RF10 Módulo predictivo | Cumplido | Regresión lineal con coeficiente de determinación |

**10 de 10 requisitos funcionales implementados.**

## Requisitos no funcionales

| Requisito | Estado | Evidencia |
|---|---|---|
| RNF1 Rendimiento | Cumplido | 0,88 s por archivo (umbral: 10 s) |
| RNF2 Disponibilidad | No aplica | Declarado fuera del alcance para un prototipo |
| RNF3 Seguridad | Cumplido | Cifrado, control por perfil y Row Level Security |
| RNF4 Escalabilidad | Cumplido | De 11 a 44 indicadores sin alterar el esquema |
| RNF5 Usabilidad | Cumplido | Interfaz responsiva · contraste WCAG AA |
| RNF6 Mantenibilidad | Cumplido | Código documentado y versionado |

## Los once indicadores, con datos

| Proceso | Indicador | Resultado | Meta | Estado |
|---|---|---:|---:|---|
| **Cambios** | Tasa de aceptación de cambios | 95,53 % | 90 % | Cumple |
| | Cambios urgentes sobre el total | 26,79 % | 30 % | Cumple |
| | Cambios con vuelta atrás | 6,95 % | 20 % | Cumple |
| | Cambios con error en certificación | 11,83 % | 20 % | Cumple |
| **Requerimientos** | Cantidad de requerimientos rechazados | 16,47 | 15 | En riesgo |
| | Tiempo medio de resolución | 17,82 d | 20 d | Cumple |
| | Porcentaje de resolución dentro de SLA | 95,73 % | 90 % | Cumple |
| **Incidentes** | Tiempo de resolución de incidente | 20,04 h | 20 h | En riesgo |
| | Capacidad de cierre de incidentes | 88,46 % | 90 % | En riesgo |
| **Demanda** | Tiempo de ciclo de gestión de demanda | 13,16 d | 15 d | Cumple |
| | Porcentaje de solicitudes evaluadas dentro de SLA | 83,58 % | 90 % | En riesgo |

**7 cumplen · 4 requieren atención · 25 períodos por indicador.**

## Origen de los datos

| Origen | Mediciones | Período |
|---|---:|---|
| Levantamiento institucional (fuente Jira) | 44 | sept 2024 – mar 2025 |
| Generadas para demostración | 239 | abr 2025 – sept 2026 |

Las mediciones generadas se registran bajo una fuente identificada como
**Simulado**, de modo que siempre puedan distinguirse de las efectivas.

---

# Parte 3 · Lo que excede lo comprometido

Estas capacidades no estaban en los requisitos, pero se incorporaron durante el
desarrollo.

## Las tres líneas de evolución, implementadas

La memoria las planteaba como trabajos futuros:

| Línea planteada | Estado actual |
|---|---|
| Integración con servidor de correo (SMTP) | Implementada y operativa |
| Conectores a fuentes de datos (Jira) | Desarrollado; requiere credenciales |
| Módulo de predicción avanzada | Robustecido con R² y volatilidad |

## Aplicación de análisis por vistas

En lugar de una pantalla única, el sistema se organiza en seis vistas que
comparten un mismo contexto de filtros:

**Resumen** · síntesis del desempeño, atención requerida y evolución
**Procesos** · desempeño por proceso, con acceso a su detalle
**Indicadores** · catálogo filtrable por estado y búsqueda
**Tendencias** · evolución histórica, proyección y mediciones registradas
**Alertas** · desviaciones con su brecha y tendencia
**Reportes** · exportación, carga e historial de cargas

Permite recorrer desde el estado general hasta la evidencia de cada indicador.

## Aseguramiento de la calidad

**201 pruebas automatizadas**, organizadas por tipo:

| Módulo | Pruebas | Verifica |
|---|---:|---|
| `test_etl.py` | 37 | Fórmulas, validaciones y normalización |
| `test_kpi.py` | 53 | Evaluación, cumplimiento y proyecciones |
| `test_seguridad.py` | 21 | Cifrado, sesiones y permisos |
| `test_api.py` | 49 | Endpoints, contratos y códigos HTTP |
| `test_e2e.py` | 41 | Integración, flujos, rendimiento y concurrencia |

Se ejecutan automáticamente ante cada cambio del repositorio.

## Seguridad más allá de lo exigido

El requisito RNF3 pedía credenciales cifradas y control por rol. Se incorporó
además **Row Level Security** sobre las nueve tablas: aunque alguien obtuviera
la clave pública del proyecto, no podría leer ni un registro.

## Trazabilidad de las operaciones

| Registro | Qué conserva |
|---|---|
| Cargas | Usuario, fecha, archivo, proceso, filas, períodos y advertencias |
| Notificaciones | Quién notificó, a quién, sobre qué indicador y en qué estado |
| Incidencias | Usuario, módulo, severidad y fecha |

## Publicación

El sistema está desplegado y accesible desde internet:

**https://web-production-ad202.up.railway.app**

Con integración continua: cada cambio ejecuta las pruebas y verifica que no se
expongan credenciales antes de integrarse.

## Repositorio

**https://github.com/FelipeVeraMeza/Tesis-FelipeVera**

---

# Parte 4 · Puntos a conversar

## Motor de base de datos

La memoria describe **Oracle Database Express Edition** y las Figuras 27 a 29
muestran Oracle SQL Developer. La implementación utiliza **PostgreSQL**.

El modelo lógico no cambió: las siete tablas, sus claves, las restricciones de
integridad y la normalización hasta 3FN se mantienen como fueron definidas.
Ambos son motores relacionales de licencia libre, y la bibliografía de la
memoria ya incluye a Momjian (2001) sobre PostgreSQL.

La capa de acceso a datos está encapsulada en un módulo, de modo que una
migración a Oracle afectaría solo a ese componente.

## Origen de los datos históricos

La memoria menciona datos sintéticos de marzo a octubre de 2025. El sistema
opera sobre las mediciones efectivas del levantamiento —septiembre de 2024 a
marzo de 2025, fuente Jira— y completa los períodos posteriores con mediciones
generadas, identificadas como tales.

## Alcance del catálogo

El levantamiento identificó 21 procesos y 44 indicadores. La memoria acota el
sistema a los 11 indicadores de los cuatro procesos críticos, que son los que
efectivamente automatiza. El resto del catálogo se conserva como contexto y el
sistema advierte cuando se consulta.

## Erratas menores

| Ubicación | Dice | Debería decir |
|---|---|---|
| Sección 7 | `KPIs_TI_Procesos_v7.xlsx` | `KPIs_TI_Procesos_v2.xlsx` |
| Sección 7 | `appy.py` | El backend se organizó en módulos |
| Sección 7 | biblioteca `oracledb` | `psycopg2` |

El detalle completo, con el texto propuesto para cada corrección, está en
`docs/correcciones_documento.md`.

---

# Cifras de referencia

| Concepto | Valor |
|---|---|
| Procesos del alcance | 4 |
| Indicadores implementados | 11 de 11 |
| Períodos por indicador | 25 (sept 2024 – sept 2026) |
| Mediciones efectivas | 44 (fuente Jira) |
| Requisitos funcionales | 10 de 10 |
| Pruebas automatizadas | 201 |
| Tiempo de procesamiento | 0,88 s (umbral: 10 s) |
| Tablas protegidas | 9 de 9 |
