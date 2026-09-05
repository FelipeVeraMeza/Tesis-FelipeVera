# Guía para la defensa

Sistema de Seguimiento y Visualización de KPIs · AFP Horizonte

Este documento reúne la evidencia que respalda cada afirmación de la memoria y
prepara las respuestas a las preguntas previsibles de la comisión.

---

## 1. Preparación previa

### Antes de entrar a la sala

```bash
# 1. Servidor de correo (permite demostrar el envío de alertas)
python backend/scripts/servidor_correo_prueba.py

# 2. Servidor de la aplicación, en otra consola
python backend/run.py

# 3. Comprobar el estado de la base de datos
python backend/scripts/init_db.py --verificar
```

Abrir <http://127.0.0.1:5000> y dejar preparadas cuatro pestañas, una por
perfil, con la sesión ya iniciada.

### Estado que debe mostrar el sistema

| Elemento | Valor esperado |
|---|---|
| Procesos | 21 (4 críticos) |
| Indicadores | 44 |
| Resultados históricos | 145 (sept-2024 a mar-2025) |
| Alertas activas | 4 |
| Tablas protegidas por RLS | 9 de 9 |

---

## 2. Guion de la demostración

Duración estimada: 8 a 10 minutos.

### Paso 1 · Autenticación y control de acceso (RF4, RNF3)

Ingresar como `gerente@horizonte.cl`.

> «El acceso se controla por perfil. Las contraseñas se almacenan cifradas con
> PBKDF2-SHA256, nunca en texto plano.»

Si conviene demostrarlo, intentar el ingreso con una contraseña incorrecta.

### Paso 2 · Vista ejecutiva (RF5)

> «El panel se adapta al perfil. El Gerente accede a una vista ejecutiva
> centrada en los cuatro procesos críticos, con el cumplimiento consolidado de
> cada uno.»

Señalar las tarjetas de cumplimiento y la cobertura de medición.

### Paso 3 · Detalle e histórico (RF9)

Abrir el gráfico de **Porcentaje de cambios urgentes**.

> «Cada indicador conserva su serie histórica. Este caso muestra siete períodos
> de datos reales extraídos de Jira: el indicador descendió de 28,8 % a 6,8 %
> entre septiembre de 2024 y marzo de 2025.»

### Paso 4 · Proyección de tendencias (RF10)

Sobre el mismo gráfico:

> «El sistema ajusta una recta por mínimos cuadrados sobre la serie y proyecta
> el período siguiente. En este indicador el ajuste alcanza un R² de 0,788, lo
> que indica una tendencia descendente sostenida y no una fluctuación
> aleatoria. La proyección se acompaña de su nivel de confiabilidad, de modo
> que el usuario sepa cuánto peso darle.»

**Importante:** conforme al alcance declarado, el análisis se mantiene en el
terreno estadístico lineal. No se incorporaron algoritmos de aprendizaje
automático.

### Paso 5 · Alertas y notificaciones (RF7)

Accionar el control de alerta (🚨) sobre un indicador desviado.

> «Los indicadores fuera de meta habilitan un control de alerta. Al accionarlo
> se despliega una ventana que identifica el indicador, el proceso, el valor
> medido, la meta y el responsable, y solicita confirmación antes de notificar.»

Confirmar el envío y **mostrar la consola del servidor de correo**, donde
aparece el mensaje recibido.

> «La memoria planteaba la integración con un servidor SMTP como línea de
> evolución. Esa integración ya está implementada: el sistema envía el correo
> efectivamente, en formato texto y HTML, a la casilla derivada del responsable
> del proceso.»

### Paso 6 · Carga de datos y ETL (RF1, RF2, RF3)

Cerrar sesión e ingresar como `analista@horizonte.cl`.

> «El perfil Analista dispone del módulo de carga. El sistema acepta archivos
> CSV y Excel, valida su estructura, aplica las fórmulas de cada indicador y
> registra los resultados.»

Cargar `docs/plantillas/cambios.csv` y mostrar el resumen.

Si se dispone de tiempo, cargar un archivo con errores para exhibir las
validaciones.

### Paso 7 · Reportes (RF6)

> «El sistema exporta los resultados en CSV y genera un reporte consolidado en
> PDF, con la síntesis, el cumplimiento por proceso y el detalle de
> indicadores, incluyendo la trazabilidad de quién lo emitió y cuándo.»

Presionar **Reporte PDF** y mostrar el archivo descargado. El botón *Ver
reporte* abre la misma información en pantalla.

### Paso 8 · Incidencias técnicas (RF8)

> «Cualquier usuario puede reportar fallas del sistema, indicando el módulo
> afectado y la severidad. El registro queda asociado al usuario y a la fecha.»

---

## 3. Preguntas previsibles

### «El documento indica Oracle XE y el sistema corre en PostgreSQL. ¿Por qué?»

**Respuesta:**

> La implementación se realizó sobre PostgreSQL, alojado en Supabase. La
> decisión respondió a la necesidad de operar sin instalación local del motor,
> lo que facilita el despliegue y la evaluación del prototipo.
>
> Lo relevante es que **el diseño no cambió**. Las siete tablas del modelo
> lógico —Rol, Usuario, Proceso_TI, Indicador_KPI, Meta_KPI, Resultado_KPI y
> Fuente_Dato—, sus claves primarias y foráneas, las restricciones de
> integridad y la normalización hasta tercera forma normal se mantienen
> exactamente como fueron definidos en las Tablas 17 a 23.
>
> Ambos son motores relacionales de licencia libre, de modo que la evaluación
> de factibilidad técnica se mantiene válida. La bibliografía de la memoria ya
> incluye a Momjian (2001) sobre PostgreSQL.
>
> Además, la capa de acceso a datos está encapsulada en un único módulo
> (`db.py`), por lo que migrar a Oracle XE afectaría solo a ese componente. Eso
> es precisamente lo que buscaba el requisito de escalabilidad RNF4.

**Si insisten en ver Oracle:** ofrecer implementarlo, señalando que el script
`01_esquema.sql` se traduce de forma directa, ya que no emplea funciones
específicas de PostgreSQL.

---

### «¿Los datos son reales o simulados?»

**Respuesta:**

> Son datos reales. El sistema opera sobre el levantamiento efectuado en la
> Gerencia de TI: 21 procesos, 44 indicadores y 145 mediciones correspondientes
> al período septiembre 2024 – marzo 2025, cuya fuente primaria es Jira.
>
> Los datos fueron anonimizados y se presentan bajo la identidad ficticia AFP
> Horizonte, conforme a las políticas de confidencialidad de la institución.

**Precisión honesta:** la memoria menciona datos sintéticos de marzo a octubre
de 2025. Corresponde a una versión previa del trabajo; posteriormente se
incorporó el catálogo real, lo que **fortalece** la validación.

---

### «¿Por qué solo 9 indicadores tienen mediciones, si hay 44?»

**Respuesta:**

> Ese es precisamente uno de los hallazgos del diagnóstico. De los 44
> indicadores catalogados en la Gerencia, únicamente 9 resultaron viables de
> medir con la información disponible en los sistemas actuales.
>
> El sistema no oculta esa situación: distingue explícitamente los indicadores
> medidos de los pendientes e informa la cobertura de cada proceso, en lugar de
> asumir valores por defecto que darían una lectura falsa del desempeño.
>
> Esa brecha entre lo que se quiere medir y lo que se puede medir es justamente
> el problema que el sistema ayuda a visibilizar.

---

### «¿Cómo se garantiza la seguridad de los datos?»

**Respuesta:**

> En tres niveles.
>
> Primero, las contraseñas se almacenan cifradas con PBKDF2-SHA256; el sistema
> nunca guarda ni transmite contraseñas en texto plano.
>
> Segundo, el acceso está controlado por perfil mediante tokens firmados, y
> cada endpoint verifica las atribuciones del usuario. Un Analista, por
> ejemplo, no puede emitir notificaciones, y un Gerente no puede cargar
> archivos.
>
> Tercero, la base de datos tiene Row Level Security activo en las nueve
> tablas, sin políticas de acceso público. Esto significa que aunque alguien
> obtuviera la clave pública del proyecto, no podría leer ni escribir dato
> alguno: el acceso queda restringido a la capa de aplicación.

**Demostración disponible:** `python backend/scripts/init_db.py --verificar` muestra las
nueve tablas protegidas.

---

### «¿El sistema cumple el requisito de rendimiento?»

**Respuesta:**

> Sí, con amplio margen. El requisito RNF1 establece un umbral de 10 segundos
> por archivo procesado. La medición arroja 0,884 segundos promedio para la
> carga y procesamiento completo. La operación más lenta es la generación del
> reporte, con 1,94 segundos en el peor caso.
>
> Estos tiempos incluyen la latencia de red hacia la base de datos alojada en
> la nube; en una instalación local serían menores.

**Demostración disponible:** `python backend/scripts/medir_rendimiento.py`

---

### «¿Qué pasa si el archivo cargado tiene errores?»

**Respuesta:**

> El sistema valida antes de registrar. Si faltan columnas obligatorias,
> rechaza el archivo completo e indica cuáles faltan. Si hay filas con
> problemas —un período mal escrito, un valor no numérico o negativo, un
> período duplicado— procesa las filas válidas y reporta cada omisión con su
> número de fila.
>
> También detecta incoherencias lógicas, como que los cambios aceptados superen
> a los solicitados.
>
> Además, recargar un período ya registrado actualiza el resultado en lugar de
> duplicarlo, lo que evita inconsistencias por cargas repetidas.

---

### «¿El sistema es escalable?»

**Respuesta:**

> El diseño se puso a prueba en la práctica. El sistema se construyó
> inicialmente con los 11 indicadores de los cuatro procesos críticos, y
> posteriormente se incorporó el catálogo completo de 44 indicadores en 21
> procesos **sin modificar la estructura de la base de datos**: los nuevos
> indicadores se agregan como registros, no como columnas ni tablas.
>
> Eso es exactamente lo que exigía el requisito RNF4.

---

### «¿Cómo verificó que el sistema funciona correctamente?»

**Respuesta:**

> En tres niveles.
>
> Primero, una batería de 95 pruebas automatizadas que verifican la lógica de
> negocio: las fórmulas de cálculo de cada indicador, las validaciones de
> integridad de los archivos, la clasificación del desempeño y el control de
> acceso por perfil. Se ejecutan sin conexión a la base de datos, de modo que
> son reproducibles en cualquier equipo.
>
> Segundo, pruebas de rendimiento con mediciones registradas, que contrastan
> los tiempos de respuesta con el umbral del requisito RNF1.
>
> Tercero, la verificación del control de acceso anónimo sobre la base de
> datos, que comprueba que ninguna tabla resulte accesible sin pasar por la
> capa de aplicación.

**Demostración disponible:** `python -m pytest`

Una prueba en particular usa la serie real del indicador «Porcentaje de cambios
urgentes» y verifica que el sistema detecte correctamente la tendencia
descendente sobre datos efectivamente medidos.

---

### «¿El código está versionado?»

**Respuesta:**

> Sí. El repositorio tiene un historial de commits organizados por capa
> arquitectónica: modelo de datos, acceso a datos, autenticación,
> procesamiento de indicadores, servicios, API, interfaz y documentación.
>
> Las credenciales quedan fuera del control de versiones mediante `.gitignore`,
> y se incluye una plantilla `.env.ejemplo` que documenta cada variable de
> configuración sin exponer valores reales.

**Demostración disponible:** `git log --oneline`

---

### «¿Qué falta para llevarlo a producción?»

**Respuesta:**

> Las tres líneas de evolución planteadas en la memoria avanzaron durante el
> desarrollo:
>
> La integración con correo (SMTP) está implementada y operativa; solo requiere
> las credenciales del servidor institucional.
>
> El conector a Jira está desarrollado, con las consultas definidas por
> proceso; requiere las credenciales de la instancia de la AFP para operar.
>
> El análisis de tendencias se robusteció con el coeficiente de determinación y
> la medición de volatilidad, manteniéndose dentro del alcance estadístico
> declarado.
>
> Para producción restan tareas propias de la organización: el despliegue en
> infraestructura institucional, la integración con el directorio corporativo
> para la autenticación, y la definición de respaldos, todo lo cual quedó
> explícitamente fuera del alcance del proyecto.

---

### «¿Por qué no usó Machine Learning?»

**Respuesta:**

> Fue una decisión de alcance declarada explícitamente en la memoria. Las
> capacidades predictivas se limitan a proyecciones estadísticas lineales sobre
> datos históricos.
>
> La razón es metodológica: con siete períodos de medición, aplicar algoritmos
> de aprendizaje automático produciría sobreajuste sin ganancia real de
> capacidad predictiva. Una regresión lineal con su coeficiente de
> determinación entrega una lectura honesta de la tendencia y, sobre todo,
> comunica cuánta confianza merece.
>
> La memoria plantea incorporar Machine Learning como trabajo futuro, una vez
> acumulado al menos un año de datos.

---

## 4. Cifras para tener presentes

| Concepto | Valor |
|---|---|
| Procesos identificados | 21 |
| Procesos críticos | 4 |
| Indicadores catalogados | 44 |
| Indicadores viables | 9 |
| Resultados históricos | 145 |
| Período cubierto | sept-2024 a mar-2025 |
| Requisitos funcionales cumplidos | 10 de 10 |
| Pruebas automatizadas | 95, todas en verde |
| Tiempo del ETL | 0,884 s (umbral: 10 s) |
| Tablas con RLS | 9 de 9 |

### Un resultado concreto que conviene citar

**Cambios urgentes sobre el total:** descendió de 28,83 % a 6,83 % entre
septiembre de 2024 y marzo de 2025, con un ajuste de tendencia R²=0,788.

Es un caso donde el sistema evidencia una mejora sostenida y no una
fluctuación puntual.

---

## 5. Qué evitar

- **No afirmar que el sistema está en producción.** Es un prototipo funcional,
  tal como declara la memoria.
- **No sobreafirmar sobre el correo.** Está implementado y funcionando, pero
  con un servidor de prueba; en la AFP requiere las credenciales del servidor
  institucional.
- **No decir que el conector a Jira "extrae datos hoy".** Está desarrollado y
  probado en su lógica, pero requiere credenciales de la instancia real.
- **No ocultar la brecha de los 9 indicadores viables.** Es un hallazgo del
  diagnóstico y conviene presentarlo como tal.
- **No entrar en detalles de implementación** salvo que se pregunten. La
  comisión evalúa la solución, no el código línea a línea.

---

## 6. Comandos de respaldo

Por si la comisión solicita una verificación en vivo:

```bash
# Estado de la base y protección de las tablas
python backend/scripts/init_db.py --verificar

# Medición de rendimiento (RNF1)
python backend/scripts/medir_rendimiento.py

# Pruebas automatizadas
python -m pytest

# Historial de versiones
git log --oneline

# Comprobar que el acceso anónimo está cerrado
curl "https://<proyecto>.supabase.co/rest/v1/usuario?select=*" \
     -H "apikey: <clave_publica>"
# Debe responder 401
```
