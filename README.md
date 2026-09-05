# Sistema de Seguimiento y Visualización de KPIs

**AFP Horizonte — Gerencia de Tecnologías de la Información**

Prototipo funcional desarrollado como proyecto de título. Automatiza la carga,
el cálculo y la visualización de los indicadores clave de desempeño (KPI) de los
cuatro procesos críticos de la Gerencia de TI.

---

## Catálogo de indicadores

El sistema opera sobre el levantamiento realizado en la Gerencia de TI,
importado desde la planilla institucional `KPIs_TI_Procesos_v2.xlsx`:

| | Cantidad |
|---|---|
| Procesos identificados | 21 (4 definidos como críticos) |
| Indicadores catalogados | 44 |
| Indicadores viables de medir | 9 |
| Indicadores con medición registrada | 34 |
| Resultados históricos | 145 (septiembre 2024 a marzo 2025) |

Los cuatro procesos críticos, que constituyen el alcance del proyecto, son
Gestión de Cambios TI, Gestión de Incidentes TI, Gestión de Requerimientos TI y
Gestión de la Demanda TI. El panel ejecutivo los presenta en primer lugar y el
resto del catálogo queda disponible en el selector de procesos.

La distinción entre indicadores medidos y no medidos se conserva: el sistema
informa la cobertura de cada proceso en lugar de asumir un valor cero para lo
que aún no se implementa.

**Cobertura de los procesos críticos:** 10 de los 11 indicadores definidos
cuentan con mediciones. El indicador *Capacidad de cierre de incidentes* está
definido en la ficha técnica y el sistema lo calcula, pero la planilla del
levantamiento no registra valores para él; aparece como *Sin datos* hasta que
se cargue el primer período.

Las fórmulas de cálculo corresponden a las fichas técnicas documentadas en las
Tablas 11 a 14 de la memoria.

### Origen de los datos

Los valores históricos provienen de las mediciones registradas en la planilla,
cuya fuente primaria es **Jira** para los procesos de cambios, incidentes y
requerimientos. Las metas expresadas como proporción (0 a 1) se convierten a
porcentaje al importarse, para mantener la coherencia con las fichas técnicas.

---

## Arquitectura

Arquitectura en cuatro capas, según lo definido en el diseño del sistema:

```
┌─────────────────────────────────────────────────────┐
│  Presentación    frontend/   HTML · CSS · JavaScript │
│                              Chart.js                │
├─────────────────────────────────────────────────────┤
│  Aplicación      backend/app/api.py    Flask (REST)  │
│                  backend/app/auth.py   Autenticación │
├─────────────────────────────────────────────────────┤
│  Procesamiento   backend/app/etl.py    ETL           │
│                  backend/app/kpi.py    Cálculo KPI   │
├─────────────────────────────────────────────────────┤
│  Almacenamiento  PostgreSQL (Supabase)               │
└─────────────────────────────────────────────────────┘
```

La comunicación entre capas sigue el patrón cliente-servidor: el navegador
consume una API REST que devuelve JSON.

---

## Estructura del proyecto

```
Proyecto_KPI/
├── .env.ejemplo                  Plantilla de configuración
├── Procfile                      Arranque en el servidor
├── railway.json                  Configuración de despliegue
├── requirements.txt
├── pytest.ini
│
├── backend/
│   ├── run.py                    Punto de entrada del servidor
│   ├── requirements.txt
│   │
│   ├── app/                      Aplicación
│   │   ├── config.py             Configuración y variables de entorno
│   │   ├── db.py                 Acceso a la base de datos
│   │   ├── auth.py               Autenticación y control de acceso (RF4)
│   │   ├── etl.py                Extracción, transformación y carga (RF1-RF3)
│   │   ├── kpi.py                Evaluación y proyecciones (RF10)
│   │   ├── notificaciones.py     Alertas de desempeño (RF7)
│   │   ├── reportes.py           Reportes consolidados (RF6)
│   │   ├── conectores.py         Extracción desde fuentes externas
│   │   └── api.py                Endpoints REST
│   │
│   ├── database/
│   │   └── migrations/           Esquema versionado
│   │       ├── 01_esquema.sql            Modelo lógico (Tablas 17-23)
│   │       ├── 02_datos_iniciales.sql    Roles, usuarios, procesos y KPI
│   │       ├── 03_seguridad_rls.sql      Row Level Security (RNF3)
│   │       ├── 04_ampliacion_catalogo.sql
│   │       ├── 05_notificaciones.sql
│   │       ├── 06_incidencias.sql
│   │       └── 07_trazabilidad_cargas.sql
│   │
│   └── scripts/                  Utilidades de operación
│       ├── init_db.py            Creación del esquema y verificación
│       ├── importar_excel.py     Importación del catálogo institucional
│       ├── medir_rendimiento.py  Medición de tiempos (RNF1)
│       └── servidor_correo_prueba.py
│
├── frontend/                     Capa de presentación
│   ├── login.html
│   ├── dashboard.html
│   ├── assets/
│   ├── css/
│   └── js/
│
├── tests/                        Pruebas automatizadas
│   ├── test_kpi.py
│   ├── test_etl.py
│   └── test_seguridad.py
│
└── docs/
    ├── despliegue.md             Publicación en Railway
    ├── manual_uso.md             Manual de usuario
    ├── guia_defensa.md           Guion y preguntas previsibles
    ├── argumentos_defensa.md     Hallazgos e impacto del trabajo
    ├── evidencia/                Salidas de respaldo
    ├── correcciones_documento.md Discrepancias con la memoria
    ├── plantillas/               Archivos CSV de ejemplo
    └── fuentes/                  Documentos institucionales (no versionados)
```

---

## Instalación y puesta en marcha

### 1. Instalar dependencias

```bash
pip install -r backend/requirements.txt
```

### 2. Crear la base de datos

```bash
python backend/scripts/init_db.py
```

El script crea las siete tablas del modelo lógico y carga los datos iniciales
(roles, usuarios, los cuatro procesos críticos y las fichas técnicas de los
once KPI).

Requiere la variable `SUPABASE_DB_PASSWORD` en el archivo `.env`. Si no está
presente, el script genera `backend/database/migrations/instalar_completo.sql` para ejecutarlo
manualmente desde el SQL Editor de Supabase.

Para comprobar el estado de la base en cualquier momento:

```bash
python backend/scripts/init_db.py --verificar
```

### 3. Importar el catálogo institucional

```bash
python backend/scripts/importar_excel.py "<ruta>/KPIs_TI_Procesos_v2.xlsx"
```

Carga los 21 procesos, los 44 indicadores con sus fichas técnicas y los 145
resultados históricos medidos entre septiembre de 2024 y marzo de 2025.
Reemplaza el catálogo existente, sin afectar a los usuarios ni a los roles.

Para revisar lo que se importaría sin escribir en la base:

```bash
python backend/scripts/importar_excel.py "<ruta>/KPIs_TI_Procesos_v2.xlsx" --simular
```

Este paso es opcional: sin él, el sistema opera con el catálogo base de los
cuatro procesos críticos definido en `02_datos_iniciales.sql`.

### 4. Levantar el servidor

```bash
python backend/run.py
```

Abrir <http://127.0.0.1:5000> en el navegador.

---

## Usuarios de prueba

| Correo | Rol | Permisos |
|---|---|---|
| `gerente@horizonte.cl` | Gerente | Vista ejecutiva consolidada |
| `lider@horizonte.cl` | Líder | Dashboards de cumplimiento y tendencias |
| `analista@horizonte.cl` | Analista | Carga de archivos y validación de datos |
| `admin@horizonte.cl` | Administrador | Administración y carga de datos |

Contraseña para todos los perfiles: `1234`

Las contraseñas se almacenan cifradas con PBKDF2-SHA256 (RNF3); el valor en
texto plano solo existe en este entorno de prueba.

---

## Carga de datos

Los perfiles **Analista** y **Administrador** disponen de la sección *Carga de
datos*. El sistema valida el archivo, aplica las fórmulas y registra los
resultados.

En `docs/plantillas/` hay un archivo por proceso con seis períodos de
datos, que sirven tanto de prueba como de plantilla.

### Formato de los archivos

Todos los archivos son CSV separados por coma, codificados en UTF-8, con una
columna `periodo` en formato `AAAA-MM`.

**cambios.csv**
```
periodo,cambios_solicitados,cambios_aceptados,cambios_urgentes,cambios_implementados,cambios_revertidos,cambios_error_certificacion
```

**incidentes.csv**
```
periodo,incidentes_creados,incidentes_cerrados,horas_totales_resolucion
```

**requerimientos.csv**
```
periodo,requerimientos_cerrados,requerimientos_rechazados,dias_totales_resolucion,requerimientos_dentro_sla
```

**demanda.csv**
```
periodo,solicitudes_totales,dias_totales_evaluacion,solicitudes_dentro_sla
```

Volver a cargar un período ya registrado actualiza el resultado en lugar de
duplicarlo.

### Trazabilidad de las cargas

Cada carga genera metadatos asociados: el usuario responsable, la fecha, el
archivo de procedencia, el proceso, las filas procesadas, los períodos cargados
y la cantidad de advertencias. El historial se consulta en `/api/cargas`.

Antes del cálculo, el sistema ordena la serie cronológicamente y detecta
valores atípicos mediante la desviación absoluta respecto a la mediana. Los
valores atípicos se informan como advertencia pero se registran igualmente,
ya que pueden corresponder a situaciones operativas reales.

---

## Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/salud` | Estado de la conexión con la base de datos |
| `POST` | `/api/login` | Autenticación; devuelve el token de sesión |
| `GET` | `/api/sesion` | Datos del usuario autenticado |
| `GET` | `/api/procesos` | Procesos de TI registrados |
| `GET` | `/api/kpis?proceso=` | Indicadores con valor, estado, histórico y proyección |
| `GET` | `/api/resumen` | Cumplimiento promedio por proceso |
| `GET` | `/api/alertas` | Indicadores fuera de meta |
| `POST` | `/api/notificar` | Emite una alerta al responsable del proceso |
| `GET` | `/api/notificaciones` | Historial de notificaciones emitidas |
| `POST` | `/api/carga` | Carga de archivo CSV y ejecución del ETL |
| `GET` | `/api/exportar?proceso=` | Exportación de resultados en CSV |
| `GET` | `/api/reporte?proceso=` | Reporte consolidado imprimible (PDF) |
| `POST` | `/api/incidencias` | Registro de una incidencia técnica |
| `GET` | `/api/incidencias` | Incidencias reportadas |
| `GET` | `/api/cargas` | Historial de cargas con su trazabilidad |
| `GET` | `/api/conectores` | Estado de las fuentes externas |
| `POST` | `/api/sincronizar` | Extracción directa desde Jira |

Salvo `/api/salud` y `/api/login`, todos los endpoints requieren un token válido
en la cabecera `Authorization: Bearer <token>`.

---

## Trazabilidad con los requisitos

| Requisito | Implementación |
|---|---|
| RF1 Carga de archivos | `etl.py` · admite CSV y Excel (.xlsx) |
| RF2 Validación automática | `etl.validar_y_leer()` · normalización con pandas/NumPy |
| RF3 Procesamiento de indicadores | `etl.CALCULADORAS` |
| RF4 Usuarios y autenticación | `auth.py` · tablas `rol` y `usuario` |
| RF5 Dashboards personalizados | Cuatro vistas diferenciadas por perfil |
| RF6 Exportación de resultados | `/api/exportar` (CSV) · `/api/reporte` (PDF) |
| RF7 Alertas automáticas | `kpi.alertas()` · panel de alertas · `notificaciones.py` |
| RF9 Seguimiento histórico | Tabla `resultado_kpi` por período |
| RF10 Módulo predictivo básico | `kpi.proyectar()` (regresión lineal) |
| RF8 Registro de incidencias | `/api/incidencias` · tabla `incidencia` |
| RNF1 Rendimiento | `medir_rendimiento.py` · máximo medido 1,94 s |
| RNF3 Seguridad | PBKDF2-SHA256 · roles · Row Level Security |
| RNF4 Escalabilidad | Nuevos KPI se agregan como registros, sin tocar el esquema |
| RNF5 Usabilidad | Interfaz responsiva |

---

## Vistas según el perfil (RF5)

El panel se adapta al perfil del usuario, conforme a los usuarios definidos en
el alcance del proyecto:

| Perfil | Vista | Enfoque inicial | Carga | Notifica | Reportes |
|---|---|---|---|---|---|
| Gerente | Ejecutiva | Procesos críticos | — | Sí | Sí |
| Líder | Consolidada | Procesos críticos | — | Sí | Sí |
| Analista | Análisis | Catálogo completo | Sí | — | Sí |
| Administrador | Administración | Catálogo completo | Sí | Sí | Sí |

Los perfiles con enfoque en procesos críticos parten mostrando esos cuatro
procesos, pero conservan acceso al catálogo completo desde el selector.

---

## Pruebas automatizadas

```bash
python -m pytest
```

**95 pruebas** que verifican la lógica de negocio del sistema:

| Módulo | Pruebas | Qué verifica |
|---|---|---|
| `test_kpi.py` | 34 | Clasificación del desempeño, cumplimiento, proyecciones y análisis de tendencia |
| `test_etl.py` | 40 | Las fórmulas, las validaciones de integridad y la normalización |
| `test_seguridad.py` | 21 | Cifrado de contraseñas, tokens de sesión y atribuciones por perfil |

Las pruebas se ejecutan sin conexión a la base de datos, de modo que validan la
lógica de forma aislada y reproducible.

Incluyen un caso construido sobre la serie real del indicador *Porcentaje de
cambios urgentes*, que comprueba la clasificación, la dirección de la tendencia
y la confiabilidad del ajuste sobre datos efectivamente medidos.

---

## Medición de rendimiento (RNF1)

```bash
python backend/scripts/medir_rendimiento.py
```

Mide los tiempos de respuesta de cada operación y los contrasta con el umbral
de 10 segundos establecido en el requisito. Resultados obtenidos sobre 5
repeticiones:

| Operación | Promedio | Máximo |
|---|---|---|
| Autenticación | 0,548 s | 0,631 s |
| Consulta de KPI (críticos) | 0,855 s | 0,955 s |
| Consulta de KPI (catálogo completo) | 0,869 s | 1,090 s |
| Carga y procesamiento ETL | 0,884 s | 1,022 s |
| Exportación CSV | 0,904 s | 1,045 s |
| Generación de reporte | 1,730 s | 1,936 s |

Todas las operaciones se completan bajo el umbral. Los tiempos incluyen la
latencia de red hacia la base de datos alojada en la nube.

---

## Módulo de alertas y notificaciones (RF7)

El sistema evalúa el estado de cada indicador y, cuando se clasifica como
*En riesgo* o *Bajo desempeño*, habilita un control de alerta (🚨) junto al
indicador, tanto en el panel superior como en la tabla de detalle.

Al accionarlo se despliega una ventana modal que identifica el indicador, su
proceso, el valor registrado, la meta comprometida y el destinatario, y solicita
confirmación antes de emitir la notificación. Una vez confirmada, se muestra el
mensaje generado y la notificación queda registrada en la tabla `notificacion`.

El destinatario corresponde al **dueño del proceso** definido en el catálogo,
de modo que la alerta llega a quien tiene responsabilidad sobre el indicador.

La emisión está restringida a los perfiles **Gerente**, **Líder** y
**Administrador**; el Analista visualiza las alertas pero no puede emitirlas.
El sistema tampoco permite notificar un indicador que cumple su meta.

### Envío por correo

En esta etapa el envío es **simulado**: la notificación se registra y se
confirma en pantalla, dejando trazabilidad de quién notificó, a quién y en qué
estado se encontraba el indicador.

La integración con un servidor SMTP está contemplada en el diseño y se
concentra en la función `_enviar_por_correo` de
[notificaciones.py](backend/app/notificaciones.py). Al implementarla, el canal
cambia de `Simulado` a `Correo` sin modificar el resto del flujo ni el modelo
de datos.

---

## Seguridad de la base de datos

El acceso a la base de datos está restringido en tres niveles, en cumplimiento
del requisito no funcional RNF3:

**1. Row Level Security (RLS)**
Las siete tablas tienen RLS habilitado y forzado, sin políticas de acceso
público definidas. En PostgreSQL, una tabla con RLS activo y sin políticas
deniega toda consulta a los roles `anon` y `authenticated`.

**2. Revocación de privilegios**
Como barrera adicional e independiente de RLS, se revocan todos los privilegios
sobre tablas, secuencias y funciones para esos roles, incluyendo los privilegios
por defecto de objetos futuros.

**3. Acceso exclusivo desde la capa de aplicación**
El navegador nunca consulta la base de datos directamente: toda petición pasa
por la API REST en Flask, que se conecta con la clave de servicio. Esa clave no
está sujeta a RLS, por lo que el backend opera con normalidad mientras el
acceso anónimo permanece cerrado.

El control de acceso por perfil (Gerente, Líder, Analista, Administrador) se
resuelve en `backend/app/auth.py`, mediante tokens firmados y decoradores de
autorización sobre cada endpoint.

Para auditar el estado de la protección:

```bash
python backend/scripts/init_db.py --verificar
```

El comando intenta leer cada tabla con la clave pública e informa si alguna
resultara accesible.

> **Nota sobre las claves.** La clave secreta (`SUPABASE_SECRET_KEY`) es de uso
> exclusivo del servidor y nunca se expone al navegador; el archivo `.env` está
> excluido del control de versiones.

---

## Alcances y limitaciones

Conforme a lo declarado en la memoria, el sistema es un **prototipo funcional**:

- La carga de datos es mediante archivos CSV; no hay conexión directa a los
  sistemas transaccionales.
- La actualización de los indicadores no es en tiempo real: depende de la
  periodicidad con que se carguen los archivos.
- El módulo predictivo se limita a proyecciones estadísticas lineales sobre la
  serie histórica; no incorpora algoritmos de Machine Learning.
- El alcance cubre los cuatro procesos críticos definidos en el diagnóstico.
- Los datos utilizados son ficticios, por las políticas de confidencialidad de
  la organización.

---

## Nota sobre el motor de base de datos

El diseño original contempla **Oracle Database Express Edition (XE)**. Esta
implementación utiliza **PostgreSQL sobre Supabase**, manteniendo íntegro el
modelo lógico: las siete tablas, sus claves primarias y foráneas, las
restricciones de integridad y la normalización hasta 3FN.

El cambio responde a que Supabase permite operar el prototipo sin instalación
local del motor, facilitando su despliegue y evaluación. La capa de acceso a
datos está encapsulada en `backend/app/db.py`, de modo que una eventual
migración a Oracle XE solo afecta a ese módulo.
