# Guion de la presentación de defensa

Duración estimada: 15 a 20 minutos · 14 diapositivas

Este guion indica, para cada diapositiva, qué contenido incluir y qué decir al
presentarla. Las diapositivas marcadas con **(opcional)** pueden omitirse si el
tiempo se acorta.

---

## Qué se conserva de la presentación de propuesta

Tu presentación anterior planteaba el proyecto en tiempo futuro. Para la
defensa, tres diapositivas siguen siendo válidas:

| Diapositiva original | Uso en la defensa |
|---|---|
| 1 · Portada | Se conserva, actualizando el subtítulo |
| 3 · Problemática y oportunidad | Se conserva casi íntegra |
| 4 · Objetivos | Se conserva, cambiando el tiempo verbal |

**Importante:** la diapositiva 8 mencionaba *Power BI* como herramienta de
dashboards. El sistema se construyó con desarrollo propio (Flask + PostgreSQL),
de modo que esa referencia debe corregirse.

---

## Diapositiva 1 · Portada

**Contenido**

```
GERENCIA DE TECNOLOGÍA – SUBGERENCIA DE PROYECTOS Y PROCESOS

Desarrollo de un sistema de visualización de KPIs
para la Gerencia de Tecnologías de la Información

Defensa de Proyecto de Título
Ingeniería Civil en Computación e Informática

Felipe Alejandro Vera Meza
Profesora guía: Samira Khazmou Nazi
```

**Qué decir** (30 s)

> Buenos días. Mi nombre es Felipe Vera y voy a presentar el desarrollo de un
> sistema de seguimiento de indicadores de desempeño para la Gerencia de
> Tecnologías de la Información de una administradora de fondos de pensiones,
> que en este trabajo se denomina AFP Horizonte por motivos de
> confidencialidad.

---

## Diapositiva 2 · Contenido

**Contenido**

```
01 · El problema
02 · Objetivos
03 · La solución construida
04 · Arquitectura
05 · Resultados con datos reales
06 · Hallazgo del diagnóstico
07 · Demostración
08 · Conclusiones
```

**Qué decir** (15 s) — enunciar el recorrido, sin detenerse.

---

## Diapositiva 3 · El problema

**Contenido** (se conserva de la propuesta)

```
SITUACIÓN INICIAL

· Indicadores dispersos en distintas herramientas
· Consolidación manual: descarga, limpieza y cálculo en planillas
· Reportes mensuales sin trazabilidad ni historial estructurado

CONSECUENCIA
Decisiones con información desactualizada y esfuerzo duplicado
```

**Qué decir** (1 min)

> El punto de partida fue el siguiente: la Gerencia de TI necesitaba hacer
> seguimiento del desempeño de sus procesos, pero la información estaba
> dispersa. Cada responsable descargaba archivos, los limpiaba a mano, aplicaba
> las fórmulas en una planilla y armaba gráficos que luego se consolidaban en
> un informe mensual.
>
> El problema no era solo el tiempo que tomaba. Era que ese proceso no dejaba
> trazabilidad: no quedaba registro de quién cargó qué dato ni cuándo, y la
> información llegaba con semanas de desfase.

---

## Diapositiva 4 · Objetivos

**Contenido** (mismo texto, en tiempo pasado)

```
OBJETIVO GENERAL
Desarrollar un sistema semi-automatizado de seguimiento y visualización
de los KPI de los procesos de TI, para fortalecer la toma de decisiones.

OBJETIVOS ESPECÍFICOS
1 · Sistematizar los indicadores de los procesos críticos
2 · Modelar los flujos de información
3 · Desarrollar los procesos de carga y transformación (ETL)
4 · Implementar los dashboards de visualización
5 · Validar el sistema mediante pruebas y escenarios
```

**Qué decir** (45 s)

> El objetivo general fue desarrollar un sistema que automatizara ese ciclo
> completo. Los objetivos específicos siguieron la lógica del proyecto:
> sistematizar los indicadores, modelar los flujos de información, construir el
> procesamiento de datos, implementar la visualización y validar el resultado.
>
> El alcance se acotó a cuatro procesos críticos: Gestión de Cambios,
> Incidentes, Requerimientos y Demanda.

---

## Diapositiva 5 · La solución construida

**Contenido**

```
SISTEMA WEB DE SEGUIMIENTO DE KPI

Carga de datos      →  CSV y Excel, con validación automática
Procesamiento       →  Cálculo de indicadores según ficha técnica
Almacenamiento      →  Base de datos relacional normalizada (3FN)
Visualización       →  Dashboards diferenciados por perfil
Alertas             →  Notificación al responsable del proceso

Desarrollado con Python (Flask), PostgreSQL y tecnologías web
```

**Qué decir** (1 min 30 s)

> El sistema construido cubre el ciclo completo. El responsable de proceso carga
> un archivo —CSV o Excel—; el sistema valida su estructura, aplica las fórmulas
> definidas en la ficha técnica de cada indicador y almacena los resultados en
> una base de datos normalizada.
>
> Desde ahí, cada usuario accede a un panel adaptado a su perfil, y cuando un
> indicador se desvía de su meta, el sistema permite notificar al responsable
> sin salir de la aplicación.
>
> Se desarrolló con Python y el framework Flask en la capa de aplicación,
> PostgreSQL para el almacenamiento, y HTML, CSS y JavaScript para la interfaz.

**Nota:** si preguntan por Oracle XE, ver la respuesta preparada en la guía de
defensa. El eje: el modelo lógico no cambió.

---

## Diapositiva 6 · Arquitectura

**Contenido** — diagrama de cuatro capas

```
┌──────────────────────────────────────────────┐
│  PRESENTACIÓN    HTML · CSS · JavaScript     │
│                  Chart.js                    │
├──────────────────────────────────────────────┤
│  APLICACIÓN      Python · Flask (API REST)   │
│                  Autenticación por perfil    │
├──────────────────────────────────────────────┤
│  PROCESAMIENTO   ETL · pandas · NumPy        │
│                  Cálculo y proyecciones      │
├──────────────────────────────────────────────┤
│  ALMACENAMIENTO  PostgreSQL                  │
│                  7 tablas · 3FN · RLS        │
└──────────────────────────────────────────────┘
```

**Qué decir** (1 min)

> La arquitectura se organizó en cuatro capas, con interfaces definidas entre
> ellas. El navegador nunca consulta la base de datos directamente: toda
> petición pasa por la API REST, que controla los permisos del usuario antes de
> responder.
>
> Esa separación tiene una consecuencia práctica: la capa de acceso a datos está
> encapsulada en un único módulo, de modo que cambiar de motor de base de datos
> afectaría solo a ese componente.

---

## Diapositiva 7 · Modelo de datos **(opcional)**

**Contenido** — diagrama entidad-relación (Figura 25 de la memoria)

```
7 TABLAS · NORMALIZADO HASTA 3FN

rol → usuario → proceso_ti → indicador_kpi → meta_kpi
                                          → resultado_kpi ← fuente_dato

Ampliado con: notificacion · incidencia
```

**Qué decir** (45 s)

> El modelo relacional conserva el diseño definido en la memoria: siete tablas
> normalizadas hasta tercera forma normal. La separación entre indicador, meta y
> resultado es la que permite mantener el historial: cada indicador acumula
> múltiples mediciones a lo largo del tiempo.

---

## Diapositiva 8 · Resultados con datos reales

**Contenido** — la diapositiva más importante

```
EL SISTEMA OPERA SOBRE DATOS REALES

  21    procesos identificados en la Gerencia
  44    indicadores catalogados
 145    mediciones históricas
        septiembre 2024 – marzo 2025

Fuente primaria: Jira
Datos anonimizados por confidencialidad
```

**Qué decir** (1 min 30 s)

> Este punto me parece el más relevante del trabajo. El sistema no se validó con
> datos inventados: opera sobre el levantamiento efectivo realizado en la
> Gerencia de TI.
>
> Son 21 procesos identificados, 44 indicadores catalogados y 145 mediciones
> reales entre septiembre de 2024 y marzo de 2025, cuya fuente primaria es Jira
> para los procesos de cambios, incidentes y requerimientos.
>
> Los datos están anonimizados por las políticas de confidencialidad de la
> institución, pero corresponden a la operación real.

---

## Diapositiva 9 · Evidencia de mejora

**Contenido** — gráfico de línea con la serie real

```
PORCENTAJE DE CAMBIOS URGENTES · Gestión de Cambios TI

sept-24  28,83 %  ████████████████████
oct-24   28,24 %  ███████████████████
nov-24   26,00 %  ██████████████████
dic-24   25,05 %  █████████████████
ene-25    4,69 %  ███
feb-25    8,91 %  ██████
mar-25    6,83 %  ████

Meta: ≤ 30 %          Reducción: 76 %          R² = 0,788
```

**Qué decir** (1 min 30 s)

> Este es un caso concreto de lo que el sistema permite observar. El porcentaje
> de cambios urgentes pasó de 28,8 % a 6,8 % en siete meses: una reducción del
> 76 %.
>
> Pero el número por sí solo no dice si eso es una tendencia real o una
> fluctuación. Por eso el sistema calcula el coeficiente de determinación: un R²
> de 0,788 indica que el ajuste lineal explica la mayor parte de la variación,
> es decir, que se trata de una mejora sostenida.
>
> El sistema no solo muestra el valor: informa cuánta confianza merece la
> tendencia observada.

---

## Diapositiva 10 · Hallazgo del diagnóstico

**Contenido**

```
BRECHA ENTRE LO DEFINIDO Y LO MEDIBLE

     44  indicadores catalogados
      9  viables de medir con los sistemas actuales

El sistema distingue explícitamente:
  · indicadores con medición registrada
  · indicadores definidos pero aún no instrumentados

No asume ceros: informa la cobertura de cada proceso
```

**Qué decir** (1 min 30 s)

> Durante el trabajo surgió un hallazgo que no estaba previsto. De los 44
> indicadores que la Gerencia tiene catalogados, solo 9 resultan viables de
> medir con la información que hoy generan sus sistemas.
>
> Esa brecha es relevante para la gestión: significa que existe una distancia
> entre lo que la organización declara medir y lo que efectivamente puede medir.
>
> El sistema no oculta esa situación. Distingue los indicadores medidos de los
> pendientes e informa la cobertura de cada proceso, en lugar de mostrar ceros
> que darían una lectura falsa del desempeño. Visibilizar esa brecha permite
> priorizar qué instrumentar primero.

---

## Diapositiva 11 · Impacto operativo **(opcional)**

**Contenido**

```
ESTIMACIÓN DEL AHORRO

                        Antes        Con el sistema
Consolidación mensual   ~4,6 h       ~8 min
Al año                  ~55 h        ~1,6 h
Latencia información    hasta 30 d   inmediata

Procesamiento medido: 0,884 s por archivo
```

**Qué decir** (1 min)

> Con el procedimiento manual, consolidar los indicadores de los cuatro procesos
> toma alrededor de 4,6 horas mensuales. Con el sistema son cuatro cargas de
> archivo: unos 8 minutos. El procesamiento en sí toma menos de un segundo,
> medido.
>
> Es una estimación conservadora, pero el beneficio mayor no es el ahorro de
> horas: es que la información deja de tener hasta 30 días de desfase.

**Advertencia:** presentarlo como estimación. Si preguntan el supuesto: 25
minutos por indicador entre descarga, limpieza, cálculo y gráfico.

---

## Diapositiva 12 · Validación

**Contenido**

```
CÓMO SE VERIFICÓ EL SISTEMA

  95  pruebas automatizadas sobre la lógica de negocio
      fórmulas · validaciones · permisos por perfil

RNF1 · Rendimiento    0,884 s  (umbral: 10 s)
RNF3 · Seguridad      contraseñas cifradas · RLS en 9 tablas
RNF4 · Escalabilidad  de 11 a 44 indicadores sin alterar el esquema

10 de 10 requisitos funcionales implementados
```

**Qué decir** (1 min)

> La validación se hizo en tres niveles. Primero, 95 pruebas automatizadas que
> verifican las fórmulas de cálculo, las validaciones de integridad y el control
> de acceso; se ejecutan sin conexión a la base de datos.
>
> Segundo, mediciones de rendimiento: el procesamiento completo toma 0,884
> segundos frente al umbral de 10 segundos del requisito.
>
> Tercero, la escalabilidad se probó en la práctica: el sistema se construyó con
> 11 indicadores y luego incorporó 44 sin modificar la estructura de la base de
> datos.

---

## Diapositiva 13 · Demostración

**Contenido** — solo un título, la pantalla pasa al sistema

```
DEMOSTRACIÓN DEL SISTEMA
```

**Guion de la demostración** (4 a 5 min)

1. **Ingreso como Gerente** — «El acceso se controla por perfil; las
   contraseñas se almacenan cifradas.»

2. **Vista ejecutiva** — señalar las tarjetas de cumplimiento y la cobertura de
   medición por proceso.

3. **Gráfico de cambios urgentes** — «Aquí está la serie que mostré recién, con
   la línea de meta y la proyección del período siguiente.»

4. **Control de alerta** — accionar la sirena sobre un indicador desviado,
   mostrar la ventana con los datos del indicador y el responsable, confirmar el
   envío y **mostrar la consola del servidor de correo** con el mensaje
   recibido.

5. **Cambio a perfil Analista** — «Este perfil dispone del módulo de carga.»
   Cargar un archivo y mostrar el resumen con las validaciones.

6. **Reporte PDF** — descargar y abrir el documento.

**Preparación previa:** ver la sección 10 de `argumentos_defensa.md`.

---

## Diapositiva 14 · Conclusiones

**Contenido**

```
CONCLUSIONES

· El ciclo completo quedó automatizado: desde la carga hasta la alerta
· Validado con 145 mediciones reales de la organización
· Verificado mediante 95 pruebas automatizadas

· Hallazgo: de 44 indicadores definidos, solo 9 son medibles hoy

LÍNEAS DE CONTINUIDAD
· Integración con el servidor de correo institucional
· Conexión directa a Jira (conector desarrollado)
· Modelo predictivo, una vez acumulado un año de datos
```

**Qué decir** (1 min 30 s)

> Para cerrar. El proyecto partió de un problema concreto: la Gerencia
> consolidaba sus indicadores a mano, con reportes que llegaban con semanas de
> desfase y sin trazabilidad.
>
> El sistema automatiza ese ciclo completo, está validado con 145 mediciones
> reales y verificado mediante 95 pruebas automatizadas.
>
> Más allá de la automatización, el trabajo dejó visible una brecha que la
> organización no tenía cuantificada: de 44 indicadores definidos, solo 9 son
> medibles hoy. Ese diagnóstico es tan valioso como la herramienta, porque
> permite priorizar qué instrumentar primero.
>
> Las tres líneas de continuidad planteadas en la memoria avanzaron durante el
> desarrollo: la integración con correo está implementada, el conector a Jira
> está desarrollado y el análisis de tendencias se robusteció.
>
> Muchas gracias. Quedo atento a sus consultas.

---

## Distribución del tiempo

| Bloque | Diapositivas | Tiempo |
|---|---|---|
| Apertura | 1–2 | 45 s |
| Problema y objetivos | 3–4 | 1 min 45 s |
| Solución y arquitectura | 5–7 | 3 min 15 s |
| Resultados y hallazgos | 8–11 | 5 min 30 s |
| Validación | 12 | 1 min |
| Demostración | 13 | 4–5 min |
| Cierre | 14 | 1 min 30 s |
| **Total** | | **~18 min** |

Si el tiempo se acorta, omitir las diapositivas 7 y 11.

---

## Recomendaciones de diseño

**Conservar la identidad visual** de tu presentación anterior: la comisión ya la
conoce y da continuidad al trabajo.

**Una idea por diapositiva.** Las cifras grandes se leen mejor que las listas
largas.

**La diapositiva 9 debe llevar un gráfico**, no una tabla. Una línea
descendente comunica de inmediato lo que una tabla de números obliga a
interpretar. Puedes capturarlo del propio sistema.

**Evitar texto que vayas a leer en voz alta.** La diapositiva sostiene lo que
dices, no lo repite.

---

## Antes de entrar

- [ ] Servidor de correo en ejecución (`servidor_correo_prueba.py`)
- [ ] Servidor de la aplicación en ejecución
- [ ] Cuatro pestañas abiertas, una por perfil, con sesión iniciada
- [ ] Un reporte PDF ya descargado, por si falla la conexión
- [ ] `python -m pytest` ejecutado, con las 95 pruebas en verde
- [ ] Carpeta `docs/evidencia/` accesible
