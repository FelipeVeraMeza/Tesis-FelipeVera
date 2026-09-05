# Correcciones a aplicar en la memoria

Discrepancias detectadas entre el documento `100%-ICCI-Felipe Vera.docx` y el
sistema efectivamente implementado. Cada punto indica dónde está el texto y con
qué reemplazarlo.

---

## 1. Motor de base de datos

**Dónde:** sección 7 *Implementación del Sistema*, subsección *Creación y
configuración de la base de datos Oracle XE*. También se menciona en Alcances,
Factibilidad Técnica, Arquitectura del Sistema y Conclusiones.

**Situación:** el documento describe Oracle Database Express Edition y las
Figuras 27 a 29 muestran Oracle SQL Developer. La implementación utiliza
PostgreSQL sobre Supabase.

**Importante:** el modelo lógico no cambió. Las siete tablas del diseño
(Tablas 17 a 23), sus claves primarias y foráneas, las restricciones de
integridad y la normalización hasta 3FN se mantienen exactamente como fueron
definidas. Solo cambia el motor que las aloja.

### Texto propuesto para reemplazar la subsección

> **Creación y configuración de la base de datos**
>
> La base de datos del sistema fue implementada sobre PostgreSQL, utilizando
> la plataforma Supabase como entorno de alojamiento. Esta decisión respondió a
> la necesidad de disponer de un entorno operativo inmediato, sin requerir la
> instalación y administración de un motor local en cada equipo, facilitando
> tanto el desarrollo como la evaluación del prototipo.
>
> La construcción del modelo físico se realizó a partir del modelo lógico
> previamente definido, transformando las entidades conceptuales en tablas
> relacionales. La estructura final incluyó las entidades Rol, Usuario,
> Proceso_TI, Indicador_KPI, Meta_KPI, Resultado_KPI y Fuente_Dato,
> manteniendo íntegramente el diseño normalizado hasta la tercera forma normal.
>
> Cada tabla fue creada mediante sentencias SQL versionadas en el repositorio
> del proyecto, lo que permite reconstruir el esquema completo de forma
> reproducible. Se implementaron secuencias para la generación automática de
> claves primarias y se establecieron claves foráneas que garantizan la
> integridad referencial entre procesos, indicadores, metas y resultados
> históricos.
>
> Adicionalmente, se aplicaron políticas de seguridad a nivel de fila (Row
> Level Security) sobre todas las tablas, de modo que el acceso a los datos
> queda restringido exclusivamente a la capa de aplicación, dando cumplimiento
> al requisito no funcional RNF3.

### Figuras a reemplazar

| Figura | Contenido actual | Reemplazar por |
|---|---|---|
| 27 | Creación de usuario en Oracle XE | Panel de Supabase con el proyecto creado |
| 28 | Código para crear base de datos en Oracle XE | Script `01_esquema.sql` en el editor |
| 29 | Vista de la base de datos en Oracle XE | Table Editor de Supabase con las tablas |

### Nota sugerida para la Factibilidad Técnica

> El motor PostgreSQL mantiene la condición de software libre considerada en el
> análisis de factibilidad, sin costos de licenciamiento. La capa de acceso a
> datos del sistema está encapsulada en un único módulo, de modo que una
> eventual migración a otro motor relacional no afecta al resto de la
> aplicación.

---

## 2. Origen y período de los datos históricos

**Dónde:** sección 7, subsección *Creación y configuración de la base de datos*.

**Texto actual:**

> «Estas mediciones fueron generadas e ingresadas como datos sintéticos para los
> meses de marzo a octubre del año 2025 (…)»

**Situación:** el sistema fue cargado con las mediciones reales registradas en
la planilla institucional, correspondientes a septiembre de 2024 a marzo de
2025. Esto **fortalece** el trabajo: los indicadores se validaron con datos
efectivamente levantados en la Gerencia de TI.

### Texto propuesto

> Durante esta fase se incorporó el catálogo de indicadores definido en el
> archivo interno KPIs_TI_Procesos_v2.xlsx, que consolida el levantamiento
> realizado en la Gerencia de TI: 21 procesos identificados, 44 indicadores
> catalogados y 145 mediciones históricas correspondientes al período
> comprendido entre septiembre de 2024 y marzo de 2025.
>
> Estas mediciones provienen de los registros operativos de la organización,
> cuya fuente primaria es la herramienta Jira para los procesos de Gestión de
> Cambios, Incidentes y Requerimientos. Los datos fueron anonimizados y
> presentados bajo la identidad ficticia AFP Horizonte, conforme a las políticas
> de confidencialidad de la institución.
>
> El uso de mediciones reales permitió validar el cálculo de los indicadores, el
> comportamiento de los gráficos de tendencia y la lógica de clasificación de
> estados sobre información representativa de la operación efectiva de la
> Gerencia.

---

## 3. Versión del archivo de KPIs

**Dónde:** sección 7, misma subsección.

**Texto actual:** `KPIs_TI_Procesos_v7.xlsx`

**Reemplazar por:** `KPIs_TI_Procesos_v2.xlsx`

Es el archivo efectivamente utilizado en la importación. La versión v7 no
existe entre los archivos del proyecto.

---

## 4. Nombre del archivo del backend

**Dónde:** sección 7, subsección *Desarrollo del backend con Python y Flask*.

**Texto actual:**

> «El archivo principal del backend, denominado appy.py (…)»

**Situación:** además de la errata (`appy.py`), el backend se organizó en
módulos separados por responsabilidad, no en un archivo único.

### Texto propuesto

> La capa de aplicación se organizó de forma modular, separando las
> responsabilidades en distintos componentes:
>
> - `api.py` — define los endpoints REST y la serialización de respuestas.
> - `db.py` — encapsula el acceso a la base de datos.
> - `auth.py` — autenticación, cifrado de contraseñas y control de acceso por rol.
> - `etl.py` — validación de archivos y cálculo de los indicadores.
> - `kpi.py` — evaluación de estados, cumplimiento y proyecciones.
> - `notificaciones.py` — emisión de alertas hacia los responsables de proceso.
> - `reportes.py` — generación de reportes consolidados.
>
> Esta separación facilita la mantenibilidad del código y el cumplimiento del
> requisito no funcional RNF6.

---

## 5. Biblioteca de conexión

**Dónde:** sección 7, misma subsección.

**Texto actual:** «La conexión permanente a Oracle mediante la biblioteca
oracledb.»

**Texto propuesto:**

> El acceso a la base de datos PostgreSQL se realiza a través de su interfaz
> REST para las operaciones de consulta y escritura, y mediante la biblioteca
> `psycopg2` para las tareas de creación y mantenimiento del esquema.

---

## 6. Alcance del catálogo de indicadores

**Dónde:** sección *Alcances*, y sección 2 *Selección y definición de KPIs*.

**Situación:** el documento se centra en 11 indicadores de cuatro procesos
críticos. El sistema implementado incorpora el catálogo completo del
levantamiento (44 indicadores en 21 procesos), destacando los cuatro procesos
críticos en el panel principal.

**Sugerencia:** conservar el alcance declarado y agregar un párrafo que
explicite el alcance ampliado, ya que constituye un resultado adicional del
trabajo.

### Párrafo propuesto para agregar en Alcances

> Si bien el análisis y la validación se concentran en los cuatro procesos
> críticos definidos, el sistema incorpora la totalidad del catálogo levantado
> en la Gerencia de TI —21 procesos y 44 indicadores— con el fin de reflejar
> fielmente la situación de la organización. El panel principal prioriza los
> procesos críticos, mientras que el resto del catálogo permanece accesible
> para consulta.
>
> Esta decisión permitió constatar un hallazgo relevante del diagnóstico: de
> los 44 indicadores catalogados, únicamente 9 resultaron viables de medir con
> la información disponible. El sistema distingue explícitamente los
> indicadores medidos de aquellos aún no implementados, informando la cobertura
> de cada proceso en lugar de asumir valores por defecto.

---

## 7. Resultados de las pruebas de rendimiento

**Dónde:** sección 7, subsección *Validación técnica de la implementación*.

**Situación:** el documento enumera las pruebas realizadas pero no presenta
resultados medidos. El requisito RNF1 establece un umbral de 10 segundos.

### Tabla propuesta para incorporar

Mediciones obtenidas con `backend/scripts/medir_rendimiento.py`, sobre 5 repeticiones
por operación:

| Operación | Promedio | Máximo | Resultado |
|---|---|---|---|
| Autenticación | 0,548 s | 0,631 s | Cumple |
| Consulta de KPI (procesos críticos) | 0,855 s | 0,955 s | Cumple |
| Consulta de KPI (catálogo completo) | 0,869 s | 1,090 s | Cumple |
| Resumen por proceso | 0,874 s | 1,022 s | Cumple |
| Consulta de alertas | 0,895 s | 1,191 s | Cumple |
| Carga y procesamiento ETL | 0,884 s | 1,022 s | Cumple |
| Exportación CSV | 0,904 s | 1,045 s | Cumple |
| Generación de reporte | 1,730 s | 1,936 s | Cumple |

### Párrafo propuesto

> Las mediciones confirman que todas las operaciones se completan holgadamente
> bajo el umbral de 10 segundos establecido en el requisito RNF1. La carga y
> procesamiento de un archivo mensual, que constituye la operación crítica del
> sistema, se resuelve en 0,884 segundos en promedio.
>
> Cabe señalar que estos tiempos incluyen la latencia de red hacia la base de
> datos alojada en la nube; en una instalación local los valores serían
> menores.

---

## 8. Funcionalidades incorporadas posteriormente

Las siguientes capacidades fueron implementadas y conviene reflejarlas en el
documento, ya que corresponden a requisitos declarados en las Tablas 15 y 16:

| Requisito | Implementación | Dónde documentarlo |
|---|---|---|
| RF1 — Carga de archivos | Admite CSV y Excel (.xlsx) | Módulo de carga y actualización de datos |
| RF5 — Dashboards personalizados | Cuatro vistas diferenciadas por perfil | Implementación del frontend |
| RF6 — Reportes y exportación | Exportación CSV y reporte consolidado imprimible en PDF | Nueva subsección |
| RF8 — Registro de incidencias | Formulario de reporte y tabla `incidencia` | Nueva subsección |
| RNF3 — Seguridad | Row Level Security sobre todas las tablas | Creación de la base de datos |

### Texto propuesto para el reporte en PDF (RF6)

> **Generación de reportes consolidados**
>
> Para dar cumplimiento al requisito de emisión de reportes, se incorporó un
> módulo que genera un documento consolidado con el estado de los indicadores,
> el cumplimiento por proceso y las desviaciones detectadas. El reporte incluye
> el alcance consultado, el período de las mediciones, la fecha de emisión y el
> usuario que lo genera, garantizando su trazabilidad.
>
> El documento se produce con estilos de impresión que permiten guardarlo
> directamente como PDF desde el navegador, manteniendo la coherencia con la
> capa de presentación del sistema sin incorporar dependencias adicionales.

### Texto propuesto para el registro de incidencias (RF8)

> **Registro de incidencias técnicas**
>
> El sistema incorpora un módulo que permite a cualquier usuario reportar
> errores o comportamientos inesperados detectados durante su uso. El formulario
> solicita el módulo afectado, la severidad, un título y una descripción del
> problema.
>
> Cada incidencia queda registrada con el usuario que la reportó y la fecha,
> quedando disponible para su revisión por parte del administrador del sistema.
> Este registro es independiente del proceso de Gestión de Incidentes TI, que
> corresponde a un proceso del negocio medido mediante sus propios indicadores.

---

## Resumen de prioridad

| Prioridad | Corrección | Motivo |
|---|---|---|
| **Alta** | 1 · Motor de base de datos | Contradicción verificable con figuras |
| **Alta** | 2 · Origen de los datos | El texto subestima el resultado obtenido |
| **Alta** | 7 · Resultados de rendimiento | RNF1 sin evidencia documentada |
| Media | 3 · Versión del archivo | Errata verificable |
| Media | 4 y 5 · Backend y biblioteca | Erratas y descripción desactualizada |
| Media | 8 · Funcionalidades nuevas | Requisitos cumplidos sin documentar |
| Baja | 6 · Alcance del catálogo | Mejora la presentación del hallazgo |
