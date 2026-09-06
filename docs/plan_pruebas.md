# Plan de aseguramiento de la calidad

Sistema de Seguimiento y Visualización de KPIs · AFP Horizonte

---

## Resumen

| Tipo de prueba | Cantidad | Dónde |
|---|---:|---|
| Funcional (fórmulas y validaciones) | 37 | `test_etl.py` |
| Funcional (evaluación y proyecciones) | 37 | `test_kpi.py` |
| Seguridad (cifrado, sesiones, permisos) | 21 | `test_seguridad.py` |
| API (endpoints, contratos, códigos HTTP) | 46 | `test_api.py` |
| Integración, E2E, rendimiento y concurrencia | 41 | `test_e2e.py` |
| **Total** | **182** | |

```bash
python -m pytest              # batería completa
python -m pytest tests/test_api.py -q   # un módulo en particular
```

---

## 1. Testing funcional

Verifica que cada función produzca el resultado esperado ante casos normales,
valores límite y entradas erróneas.

### Fórmulas de cálculo

Cada indicador se contrasta contra su ficha técnica (Tablas 11 a 14):

| Caso | Verificación |
|---|---|
| Cálculo normal | Los once indicadores devuelven el valor correcto |
| Denominador correcto | «Vuelta atrás» se calcula sobre implementados, no sobre solicitados |
| División por cero | Un período sin actividad no interrumpe el proceso |
| Indicador de conteo | «Requerimientos rechazados» es sumatoria, no porcentaje |

### Validación de archivos

| Situación | Comportamiento esperado |
|---|---|
| Faltan columnas obligatorias | Se rechaza el archivo completo |
| Período inválido (`2025-13`, `abc`, vacío) | Se omite la fila y se informa |
| Valor no numérico o negativo | Se omite la fila y se informa |
| Período duplicado | Se conserva el primero |
| Subconjunto mayor que el total | Se procesa, dejando constancia |
| Coma decimal | Se admite (Excel en español) |
| Marcador de orden de bytes (BOM) | Se ignora |

### Evaluación del desempeño

Se comprueban las tres bandas de estado en ambas tendencias —ascendente y
descendente—, incluidos los valores exactamente en el límite del margen.

### Normalización de series

| Caso | Verificación |
|---|---|
| Archivo desordenado | La serie se ordena cronológicamente |
| Valor atípico | Se detecta y se informa, sin descartar el dato |
| Serie estable | No genera falsas advertencias |
| Serie corta | No se juzga con menos de cuatro períodos |

---

## 2. Testing de integración

Comprueba que la interfaz, la API, la lógica de negocio y la base de datos
operen correctamente entre sí.

| Verificación | Propósito |
|---|---|
| La base responde y tiene esquema | Conectividad efectiva |
| El catálogo está cargado | Los datos llegan desde la base |
| Los cuatro procesos críticos están marcados | Integridad del alcance |
| Cada indicador referencia un proceso existente | Integridad referencial |
| El histórico está ordenado | Consistencia de la serie |
| El valor actual es la última medición | Coherencia del cálculo |

### Consistencia entre vistas

Las distintas pantallas deben concordar:

- Las alertas coinciden exactamente con los indicadores desviados.
- El resumen por proceso concuerda con el detalle de indicadores.
- El estado general concuerda con el conteo real.
- Un indicador sin mediciones no declara cumplimiento.

Esta última comprobación es relevante: sin ella, un indicador no instrumentado
aparecería como si el proceso rindiera cero.

---

## 3. Testing de regresión

La batería completa se ejecuta ante cada cambio, de modo que una modificación
no deteriore lo que ya funcionaba. El flujo de integración continua lo
automatiza en cada envío al repositorio.

Las pruebas unitarias operan sin base de datos ni servidor, por lo que se
ejecutan en segundos y pueden correrse sin conexión.

---

## 4. Testing de seguridad

| Aspecto | Verificación |
|---|---|
| Cifrado | La contraseña nunca se almacena en texto plano |
| Sal | Dos cifrados de la misma clave difieren entre sí |
| Sesiones | Un token alterado o sin firma se rechaza |
| Expiración | Una sesión vencida deja de ser válida |
| Entradas mal formadas | No producen errores en el sistema |
| Atribuciones | Cada perfil tiene exactamente sus permisos |
| Endpoints | Toda operación exige sesión válida |
| Exposición | Ninguna respuesta contiene credenciales |

### Control de acceso por perfil

| Operación | Gerente | Líder | Analista | Administrador |
|---|:---:|:---:|:---:|:---:|
| Consultar indicadores | Sí | Sí | Sí | Sí |
| Notificar desviaciones | Sí | Sí | **No** | Sí |
| Cargar archivos | **No** | **No** | Sí | Sí |
| Exportar reportes | Sí | Sí | Sí | Sí |

Cada restricción se verifica en ambos sentidos: que el perfil autorizado pueda
operar y que el no autorizado reciba un rechazo.

### Protección de la base de datos

Las nueve tablas tienen Row Level Security activo, sin políticas de acceso
público. El script `init_db.py --verificar` comprueba, con la clave pública,
que ninguna resulte accesible.

---

## 5. Testing de rendimiento

El requisito RNF1 establece un umbral de 10 segundos por operación.

| Operación | Promedio | Máximo |
|---|---:|---:|
| Autenticación | 0,53 s | 0,63 s |
| Consulta de indicadores (críticos) | 0,94 s | 1,11 s |
| Consulta del catálogo completo | 0,85 s | 0,91 s |
| Resumen por proceso | 0,92 s | 1,13 s |
| Carga y procesamiento ETL | 0,96 s | 1,24 s |
| Exportación CSV | 0,91 s | 1,00 s |
| Generación del reporte | 1,67 s | 1,84 s |

```bash
python backend/scripts/medir_rendimiento.py
```

Los tiempos incluyen la latencia de red hacia la base de datos alojada en la
nube. Las pruebas de extremo a extremo verifican estos umbrales de forma
automática.

### Concurrencia

- Seis consultas simultáneas se resuelven correctamente.
- Cuatro sesiones de perfiles distintos conservan cada una su identidad.

---

## 6. Testing de API

Cada endpoint se verifica en su contrato completo: código de respuesta,
estructura de los datos y comportamiento ante solicitudes mal formadas.

| Situación | Código esperado |
|---|---|
| Operación correcta | `200` / `201` |
| Solicitud incompleta o mal formada | `400` |
| Sin sesión o token inválido | `401` |
| Perfil sin atribución | `403` |
| Recurso inexistente | `404` |
| Operación improcedente | `422` |

Ejemplos de casos verificados:

- Notificar un indicador que cumple su meta → `422`
- Cargar un archivo con extensión no admitida → `400`
- Registrar una incidencia sin descripción → `400`
- Sincronizar con un período mal escrito → `400`

Estas pruebas sustituyen la capa de datos por valores controlados, de modo que
verifican el comportamiento de la API sin depender de la base.

---

## 7. Testing de extremo a extremo

Reproduce recorridos completos, tal como los realiza un usuario.

**Flujo del gerente**
Ingresar → revisar el estado general → consultar las alertas → acceder al
detalle del indicador desviado.

**Flujo del analista**
Ingresar → cargar un archivo → verificar el resultado → comprobar que la carga
quedó registrada con su responsable en el historial.

**Flujo de exportación**
Generar el CSV y el PDF, verificando que el documento sea válido.

**Flujo de incidencias**
Registrar una incidencia y confirmar que aparece en el listado.

---

## 8. Pruebas de aceptación

Contrastan el sistema con los requisitos declarados en la memoria.

| Requisito | Cómo se verifica |
|---|---|
| RF1 Carga de archivos | Pruebas de carga en CSV y Excel |
| RF2 Validación automática | Doce casos de validación |
| RF3 Procesamiento de indicadores | Las once fórmulas contra su ficha técnica |
| RF4 Usuarios y autenticación | Cifrado, sesiones y perfiles |
| RF5 Dashboards personalizados | Atribuciones por perfil |
| RF6 Reportes y exportación | CSV y PDF verificados |
| RF7 Alertas automáticas | Detección, notificación y control de acceso |
| RF8 Registro de incidencias | Registro y consulta |
| RF9 Seguimiento histórico | Orden y consistencia de la serie |
| RF10 Módulo predictivo | Proyección, ajuste y límites |
| RNF1 Rendimiento | Umbral verificado en cada operación |
| RNF3 Seguridad | Cifrado, permisos y RLS |
| RNF4 Escalabilidad | De 11 a 44 indicadores sin alterar el esquema |

---

## 9. Monitoreo y auditoría

### Estado del sistema

El endpoint `/api/salud` informa la conectividad y si el esquema está creado.
No requiere autenticación, de modo que puede consultarse desde herramientas de
supervisión externas.

```bash
curl https://<dominio>/api/salud
```

### Registro de operaciones

| Tabla | Qué registra |
|---|---|
| `fuente_dato` | Cada carga: usuario, fecha, archivo, proceso, filas, períodos y advertencias |
| `notificacion` | Cada alerta emitida: quién notificó, a quién, sobre qué indicador y en qué estado |
| `incidencia` | Cada falla reportada: usuario, módulo, severidad y fecha |

Esto permite responder qué ocurrió, cuándo y quién lo ejecutó.

Consultables en `/api/cargas`, `/api/notificaciones` e `/api/incidencias`.

### Verificación del estado

```bash
python backend/scripts/init_db.py --verificar
```

Informa los registros de cada tabla y comprueba que ninguna sea accesible con
la clave pública.

---

## 10. Integración continua

Dos flujos automatizados se ejecutan ante cada cambio en el repositorio:

**`pruebas.yml`** — compila el código y ejecuta las tres baterías: unitarias,
de API y de extremo a extremo.

**`calidad.yml`** — revisión estática en busca de errores reales (no
preferencias de estilo) y comprobación de que no haya credenciales en archivos
versionados.

Un cambio que rompa una prueba o exponga una credencial detiene el flujo antes
de integrarse.

---

## 11. Ejecución local

```bash
# Batería completa
python -m pytest

# Solo las pruebas sin dependencias externas
python -m pytest tests/test_kpi.py tests/test_etl.py tests/test_seguridad.py

# Pruebas de extremo a extremo (requieren el servidor en ejecución)
python backend/run.py
python -m pytest tests/test_e2e.py -v

# Medición de rendimiento
python backend/scripts/medir_rendimiento.py
```

Las pruebas de extremo a extremo se omiten solas si el servidor no responde,
de modo que la batería principal siempre pueda ejecutarse.
