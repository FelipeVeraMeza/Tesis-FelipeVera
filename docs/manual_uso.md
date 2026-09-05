# Manual de uso del sistema

**Sistema de Seguimiento y Visualización de KPIs — AFP Horizonte**

---

## 1. Puesta en marcha

### Requisitos previos

- Python 3.10 o superior
- Conexión a internet (la base de datos está alojada en Supabase)

### Primera ejecución

```bash
pip install -r backend/requirements.txt
python backend/scripts/init_db.py
python backend/run.py
```

Luego abrir <http://127.0.0.1:5000>.

En ejecuciones posteriores basta con el último comando.

### Verificar el estado del sistema

```bash
python backend/scripts/init_db.py --verificar
```

Muestra si hay conexión, si el esquema está creado y cuántos registros tiene
cada tabla.

---

## 2. Inicio de sesión

El sistema presenta cuatro perfiles, cada uno con permisos distintos:

| Perfil | Correo | Qué puede hacer |
|---|---|---|
| Gerente | `gerente@horizonte.cl` | Consultar todos los indicadores, alertas y exportar |
| Líder | `lider@horizonte.cl` | Consultar indicadores, alertas y exportar |
| Analista | `analista@horizonte.cl` | Todo lo anterior **más** cargar archivos CSV |
| Administrador | `admin@horizonte.cl` | Todo lo anterior |

Contraseña de todos los perfiles: `1234`

La sección *Carga de datos* solo aparece para los perfiles Analista y
Administrador. Si un usuario sin permiso intenta cargar un archivo, el servidor
responde con un error 403.

---

## 3. Panel de control

### Alertas de desempeño

Aparece en la parte superior cuando hay indicadores fuera de meta. Se lista el
proceso, el indicador, su valor actual y la meta comprometida.

### Cumplimiento por proceso

Una tarjeta por cada proceso crítico, con el cumplimiento promedio de sus
indicadores. El color del borde superior indica la situación:

| Color | Significado |
|---|---|
| Verde | 90 % o más |
| Ámbar | Entre 75 % y 89 % |
| Rojo | Bajo 75 % |

### Detalle de indicadores

Tabla con el valor del último período, la meta, la tendencia esperada, el estado
y la proyección del período siguiente.

El estado se determina comparando el valor con la meta, considerando si el
indicador es ascendente o descendente:

| Estado | Indicador ascendente | Indicador descendente |
|---|---|---|
| Cumple | valor ≥ meta | valor ≤ meta |
| En riesgo | valor ≥ 80 % de la meta | valor ≤ 120 % de la meta |
| Bajo desempeño | por debajo de ese margen | por encima de ese margen |

El botón **Ver gráfico** muestra la evolución histórica del indicador, la línea
de meta y la proyección.

### Notificar una desviación (RF7)

Los indicadores clasificados como *En riesgo* o *Bajo desempeño* muestran un
control de alerta (🚨), tanto en el panel superior como en la columna *Alerta*
de la tabla.

Al accionarlo se abre una ventana que identifica:

- el indicador y su proceso,
- el valor registrado y la meta comprometida,
- el estado del indicador,
- el destinatario de la notificación (el dueño del proceso).

Tras confirmar, el sistema registra la notificación y muestra el mensaje que se
envía al responsable.

**Quién puede notificar:** Gerente, Líder y Administrador. El Analista visualiza
las alertas pero no dispone del control de envío. Tampoco es posible notificar
un indicador que cumple su meta.

**Sobre el envío:** si hay un servidor de correo configurado en el archivo
`.env`, el sistema envía la notificación efectivamente, en formato texto y
HTML, a la casilla del responsable. Sin esa configuración, la notificación
queda registrada en la base de datos y se confirma en pantalla, indicando que
el envío fue simulado.

Para probar el envío sin un servidor institucional:

```bash
python backend/scripts/servidor_correo_prueba.py
```

Luego, en el archivo `.env`: `SMTP_HOST=localhost`, `SMTP_PUERTO=1025` y
`SMTP_TLS=False`. Los correos recibidos se muestran en la consola y se guardan
en `backend/correos_recibidos/`.

### Filtro y exportación

El selector superior filtra por proceso.

- **Exportar CSV** descarga los indicadores con todos sus atributos.
- **Reporte PDF** descarga un documento consolidado con la síntesis, el
  cumplimiento por proceso y el detalle de indicadores.
- **Ver reporte** abre esa misma información en pantalla, sin descargarla.

El reporte registra el alcance consultado, el período de las mediciones, la
fecha de emisión y el usuario que lo genera.

### Reportar una incidencia técnica (RF8)

El botón **Reportar incidencia**, en la barra superior, permite informar
cualquier error o comportamiento inesperado del sistema. El formulario solicita:

- el módulo afectado (Dashboard, Carga de datos, Reportes, Alertas u Otro),
- la severidad (Alta, Media o Baja),
- un título breve y una descripción del problema.

La incidencia queda registrada con el usuario que la reportó y la fecha, en
estado *Abierta*, para su revisión por el administrador del sistema.

Está disponible para todos los perfiles.

---

## 4. Carga de datos

1. Seleccionar el proceso correspondiente.
2. Elegir el archivo CSV.
3. Presionar **Procesar archivo**.

El sistema valida el archivo, calcula los indicadores y muestra un resumen con
las filas procesadas, los períodos cargados y las advertencias detectadas.

### Formato de los archivos

Archivos CSV separados por coma, en codificación UTF-8, con una columna
`periodo` en formato `AAAA-MM`.

**Gestión de Cambios**
```
periodo, cambios_solicitados, cambios_aceptados, cambios_urgentes,
cambios_implementados, cambios_revertidos, cambios_error_certificacion
```

**Gestión de Incidentes**
```
periodo, incidentes_creados, incidentes_cerrados, horas_totales_resolucion
```

**Gestión de Requerimientos**
```
periodo, requerimientos_cerrados, requerimientos_rechazados,
dias_totales_resolucion, requerimientos_dentro_sla
```

**Gestión de Demanda**
```
periodo, solicitudes_totales, dias_totales_evaluacion, solicitudes_dentro_sla
```

En `docs/plantillas/` hay un archivo por proceso que sirve de plantilla.

### Validaciones aplicadas

| Situación | Comportamiento |
|---|---|
| Faltan columnas obligatorias | Se rechaza el archivo completo |
| Período mal escrito (`2025-13`, `abc`) | Se omite la fila y se informa |
| Valor no numérico o negativo | Se omite la fila y se informa |
| Período repetido dentro del archivo | Se omite la fila duplicada |
| Un subconjunto supera al total | Se procesa pero se advierte |
| División por cero | El indicador no se registra y se informa |

Volver a cargar un período ya registrado **actualiza** el resultado; no se
generan duplicados.

---

## 5. Cálculo de los indicadores

| Proceso | Indicador | Fórmula |
|---|---|---|
| Cambios | Tasa de aceptación | Aceptados / Solicitados × 100 |
| Cambios | Cambios urgentes | Urgentes / Total × 100 |
| Cambios | Vuelta atrás | Revertidos / Implementados × 100 |
| Cambios | Error en certificación | Con error / Implementados × 100 |
| Incidentes | Tiempo de resolución | Horas totales / Cerrados |
| Incidentes | Capacidad de cierre | Cerrados / Creados × 100 |
| Requerimientos | Rechazados | Sumatoria de rechazados |
| Requerimientos | Tiempo medio de resolución | Días totales / Cerrados |
| Requerimientos | Resolución dentro de SLA | Dentro de SLA / Cerrados × 100 |
| Demanda | Tiempo de ciclo | Días totales / Solicitudes |
| Demanda | Evaluadas dentro de SLA | Dentro de SLA / Total × 100 |

Estas fórmulas corresponden a las fichas técnicas de las Tablas 11 a 14 de la
memoria.

---

## 6. Proyección de tendencias

La proyección se calcula mediante regresión lineal por mínimos cuadrados sobre
la serie histórica del indicador, y estima el valor del período siguiente.

Requiere al menos tres períodos registrados; con menos datos la columna
*Proyección* muestra un guion.

Conforme al alcance declarado, se trata de una proyección estadística lineal:
no incorpora algoritmos de Machine Learning.

---

## 7. Problemas frecuentes

**No se pudo contactar al servidor**
El backend no está en ejecución. Levantarlo con `python backend/run.py`.

**Aparece la tabla vacía**
No hay resultados cargados. Cargar los archivos de `docs/plantillas/` desde
el perfil Analista.

**Error al iniciar sesión con credenciales correctas**
La base de datos no tiene los usuarios. Ejecutar `python backend/scripts/init_db.py`.

**El archivo no se procesa**
Revisar que las columnas coincidan exactamente con el formato de la sección 4 y
que el archivo esté guardado en UTF-8. Excel debe exportarse como
*CSV UTF-8 (delimitado por comas)*.

---

## 8. Escenarios de prueba sugeridos

Para el capítulo de validación del sistema:

| Nº | Escenario | Resultado esperado |
|---|---|---|
| 1 | Ingresar con credenciales válidas | Acceso al panel según el rol |
| 2 | Ingresar con contraseña incorrecta | Mensaje "Credenciales inválidas" |
| 3 | Acceder al panel sin sesión | Redirección al inicio de sesión |
| 4 | Cargar un CSV válido | Resultados registrados y panel actualizado |
| 5 | Cargar un CSV sin columnas obligatorias | Archivo rechazado, indicando las faltantes |
| 6 | Cargar un CSV con períodos inválidos | Filas válidas procesadas, resto advertido |
| 7 | Recargar un período ya existente | Resultado actualizado, sin duplicados |
| 8 | Intentar cargar como Gerente | Acceso denegado (403) |
| 9 | Filtrar por proceso | Solo los indicadores de ese proceso |
| 10 | Exportar a CSV | Archivo descargado con los indicadores |
| 11 | Consultar un KPI bajo meta | Aparece en el panel de alertas |
| 12 | Ver gráfico de un indicador | Serie histórica, meta y proyección |
| 13 | Leer la tabla `usuario` con la clave pública | Acceso denegado (401) |
| 14 | Insertar un resultado con la clave pública | Acceso denegado (401) |
| 15 | Ver un KPI en riesgo como Gerente | Aparece el control de alerta 🚨 |
| 16 | Accionar el control de alerta | Se abre la ventana con los datos del indicador |
| 17 | Confirmar el envío de la notificación | Confirmación en pantalla y registro en la base |
| 18 | Ver un KPI en riesgo como Analista | El control de alerta no está disponible |
| 19 | Notificar un indicador que cumple su meta | Operación rechazada (422) |
| 20 | Consultar el historial de notificaciones | Lista con emisor, destinatario y fecha |
| 21 | Ingresar con cada perfil | El panel muestra el enfoque correspondiente |
| 22 | Cargar un archivo Excel (.xlsx) | Se procesa igual que un CSV |
| 23 | Cargar un archivo con otra extensión | Formato rechazado (400) |
| 24 | Generar el reporte consolidado | Documento con síntesis y detalle |
| 25 | Registrar una incidencia técnica | Confirmación con número de incidencia |
| 26 | Registrar una incidencia incompleta | Solicitud rechazada (400) |
| 27 | Medir los tiempos de respuesta | Todas las operaciones bajo 10 s (RNF1) |
| 28 | Descargar el reporte en PDF | Archivo PDF válido, con varias páginas |
| 29 | Ejecutar la batería de pruebas | 89 pruebas en verde |

---

## 9. Pruebas de seguridad de la base de datos

Estas pruebas verifican el cumplimiento del RNF3 y pueden documentarse en el
capítulo de validación.

### Auditoría automática

```bash
python backend/scripts/init_db.py --verificar
```

Debe informar las siete tablas como *protegida*.

### Verificación manual

Intento de lectura de la tabla de usuarios empleando la clave pública, que es
la única que llegaría a un navegador:

```bash
curl "https://<proyecto>.supabase.co/rest/v1/usuario?select=*" \
     -H "apikey: <clave_publica>"
```

**Resultado esperado:** `HTTP 401` con el mensaje
`permission denied for table usuario`.

### Resultados obtenidos

| Prueba | Antes de aplicar RLS | Después |
|---|---|---|
| Leer `usuario` (correos y hashes) | 200 — datos expuestos | 401 — denegado |
| Leer `indicador_kpi` | 200 — datos expuestos | 401 — denegado |
| Insertar en `resultado_kpi` | Permitido | 401 — denegado |
| Operación normal del sistema | Correcta | Correcta |

La última fila es relevante: la protección no altera el funcionamiento de la
aplicación, porque el backend accede con la clave de servicio, que no está
sujeta a las políticas de RLS.

---

## 10. Pruebas del módulo de alertas

Resultados obtenidos sobre el endpoint `POST /api/notificar`:

| Perfil / caso | Respuesta | Interpretación |
|---|---|---|
| Gerente notifica un KPI en alerta | `200` | Notificación registrada |
| Líder notifica un KPI en alerta | `200` | Notificación registrada |
| Analista intenta notificar | `403` | Perfil sin atribución de envío |
| Petición sin identificador | `400` | Solicitud incompleta |
| Petición sin sesión | `401` | Requiere autenticación |
| Notificar un KPI que cumple su meta | `422` | No corresponde emitir alerta |

Cada notificación registra el indicador, su estado, el valor medido, la meta,
el destinatario, el emisor y la fecha, lo que permite auditar quién notificó
qué desviación y cuándo.

La tabla `notificacion` está protegida por Row Level Security, igual que el
resto del modelo.
