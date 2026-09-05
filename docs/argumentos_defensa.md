# Argumentos de defensa

Material complementario a la guía de defensa. Reúne los puntos donde el
trabajo tiene ventaja demostrable y la forma de presentarlos.

---

## 1. La ventaja principal: datos reales

La mayoría de los proyectos de título se validan con datos inventados. Este no.

| | |
|---|---|
| Mediciones | 145 registros efectivos |
| Período | septiembre 2024 a marzo 2025 |
| Fuente | Jira, sistema productivo de la organización |
| Responsables | personas identificadas en el levantamiento |

**Cómo plantearlo, sin sobreafirmar:**

> «El sistema no se validó con datos simulados. Opera sobre 145 mediciones
> reales levantadas en la Gerencia de TI entre septiembre de 2024 y marzo de
> 2025, cuya fuente primaria es Jira. Los datos están anonimizados por las
> políticas de confidencialidad de la institución, pero corresponden a la
> operación efectiva.»

Esto cambia la naturaleza de la conversación: ya no se discute si el sistema
*podría* funcionar, sino qué muestra sobre la operación real.

---

## 2. Un hallazgo que el sistema hizo visible

De 44 indicadores catalogados, **solo 9 resultan viables de medir** con la
información disponible hoy. Es decir, la Gerencia declara medir 44 cosas y
puede medir 9.

**No es una debilidad del trabajo: es su hallazgo más valioso.**

> «Uno de los resultados del diagnóstico fue constatar una brecha entre lo que
> la Gerencia define medir y lo que efectivamente puede medir: de 44
> indicadores catalogados, solo 9 son viables con los sistemas actuales.
>
> El sistema no oculta esa brecha. Distingue explícitamente los indicadores
> medidos de los pendientes e informa la cobertura de cada proceso, en lugar de
> mostrar ceros que darían una lectura falsa del desempeño.
>
> Visibilizar esa brecha es, en sí mismo, un aporte a la gestión: permite
> priorizar qué instrumentar primero.»

**Si preguntan por qué no se midieron los 44:** porque no existe la fuente de
datos. No es un problema de desarrollo, sino de instrumentación de los
procesos, y excede el alcance del proyecto.

---

## 3. Evidencia de mejora sostenida

El caso más sólido del conjunto:

**Porcentaje de cambios urgentes** — Gestión de Cambios TI

| Período | Valor |
|---|---|
| sept-2024 | 28,83 % |
| oct-2024 | 28,24 % |
| nov-2024 | 26,00 % |
| dic-2024 | 25,05 % |
| ene-2025 | 4,69 % |
| feb-2025 | 8,91 % |
| mar-2025 | 6,83 % |

Reducción del **76 %**, con un ajuste de tendencia **R² = 0,788**.

> «Este indicador pasó de 28,8 % a 6,8 % en siete meses. El coeficiente de
> determinación de 0,788 respalda que se trata de una tendencia sostenida y no
> de una fluctuación puntual. El sistema no solo muestra el número: informa
> cuánta confianza merece la tendencia observada.»

### Otros movimientos del período

| Indicador | Variación | Ajuste |
|---|---|---|
| Cambios con vuelta atrás | 1,49 % → 0 % | R²=0,509 (media) |
| Errores en certificación | 4,47 % → 3,11 % | R²=0,026 (baja) |
| Tiempo de resolución de incidentes | 13,6 → 14,6 h | R²=0,689 (media) |

**Importante:** el último caso muestra un deterioro. Conviene mencionarlo si
surge, en lugar de presentar solo lo favorable:

> «No todos los indicadores mejoran. El tiempo de resolución de incidentes
> subió un 7 % en el período, con un ajuste de 0,689 que sugiere una tendencia
> real. Precisamente para eso sirve el sistema: la desviación queda visible y
> el responsable recibe la alerta.»

Reconocer un dato desfavorable refuerza la credibilidad del resto.

---

## 4. Impacto operativo

Estimación conservadora, basada en el proceso manual que describe el documento:

| | Situación actual | Con el sistema |
|---|---|---|
| Consolidación mensual | ~4,6 h | ~8 min |
| Al año | ~55 h | ~1,6 h |
| Latencia de la información | hasta 30 días | inmediata tras la carga |

**Ahorro estimado: 53 horas anuales, equivalentes a 7 jornadas laborales.**

> «Con el procedimiento actual, consolidar los 11 indicadores de los procesos
> críticos toma alrededor de 4,6 horas mensuales entre descarga, limpieza,
> cálculo y armado de gráficos. Con el sistema, son cuatro cargas de archivo:
> unos 8 minutos. El procesamiento en sí toma 0,884 segundos, medidos.
>
> El ahorro es de unas 53 horas al año, pero el beneficio mayor no es ese: es
> que la información deja de tener hasta 30 días de desfase.»

**Advertencia:** presentar la cifra como estimación, no como medición. Si
preguntan de dónde sale, explicar el supuesto (25 minutos por indicador) y
señalar que es conservador.

---

## 5. Lo que distingue técnicamente al trabajo

Puntos que no suelen aparecer en un proyecto de título y conviene mencionar
solo si la conversación lo permite:

**Seguridad a nivel de base de datos.** No basta con controlar el acceso en la
aplicación: las nueve tablas tienen Row Level Security, de modo que aunque
alguien obtuviera la clave pública del proyecto no podría leer ni un registro.

**Pruebas automatizadas.** 95 pruebas sobre la lógica de negocio, ejecutables
sin conexión a la base de datos. Incluyen un caso construido sobre la serie
real del indicador de cambios urgentes.

**Honestidad estadística.** La proyección se acompaña de su coeficiente de
determinación. Un R² de 0,026 se informa como *confiabilidad baja*, en lugar de
presentar el número como si fuera igual de sólido que uno con R² de 0,788.

**Escalabilidad demostrada, no declarada.** El sistema se construyó con 11
indicadores y luego incorporó 44 en 21 procesos sin modificar el esquema de la
base de datos. El requisito RNF4 no quedó como afirmación: se probó.

---

## 6. Las tres líneas de evolución, ya implementadas

El documento plantea tres trabajos futuros. Los tres avanzaron:

| Línea planteada | Estado |
|---|---|
| Integración con servidor de correo (SMTP) | Implementada y operativa |
| Conectores a fuentes de datos (Jira) | Desarrollado, requiere credenciales |
| Módulo de predicción avanzada | Robustecido con R² y volatilidad |

> «Las tres líneas de evolución planteadas en la memoria avanzaron durante el
> desarrollo. El envío de correo está implementado y funcionando; puedo
> demostrarlo. El conector a Jira está desarrollado con las consultas definidas
> por proceso, y requiere únicamente las credenciales de la instancia de la
> AFP. El análisis de tendencias se robusteció manteniéndose dentro del alcance
> estadístico declarado.»

**Cuidado:** no afirmar que el conector «extrae datos hoy». Está desarrollado y
probado en su lógica, pero sin credenciales no opera contra Jira.

---

## 7. Cómo manejar las preguntas difíciles

### Regla general

Reconocer primero, explicar después. Un evaluador detecta de inmediato cuando
se esquiva una pregunta, y eso cuesta más que la limitación misma.

### «El sistema no está en producción»

> «Correcto, y así está declarado en el alcance: es un prototipo funcional. El
> despliegue en infraestructura institucional, la integración con el directorio
> corporativo y la definición de respaldos quedaron explícitamente fuera del
> alcance, porque dependen de decisiones de la organización.»

### «Usó PostgreSQL y el documento dice Oracle»

Ver la respuesta desarrollada en la guía de defensa. El eje del argumento:
**el modelo lógico no cambió**, y la bibliografía ya incluye a Momjian sobre
PostgreSQL.

### «Esto se podría haber hecho en Power BI»

> «La organización ya cuenta con un tablero en Power BI, que fue el punto de
> partida del levantamiento. La diferencia es que ese tablero se alimenta de
> planillas actualizadas a mano y no conserva historial estructurado ni
> trazabilidad de quién cargó qué.
>
> Este sistema aporta la capa que faltaba: validación automática de los datos,
> almacenamiento normalizado con historial por período, trazabilidad de cada
> carga, control de acceso por perfil y alertas hacia los responsables. Es
> complementario, no un reemplazo.»

### «¿Por qué no usó Machine Learning?»

> «Fue una decisión de alcance, declarada en la memoria. Con siete períodos de
> medición, aplicar aprendizaje automático produciría sobreajuste sin ganancia
> predictiva real. Una regresión lineal con su coeficiente de determinación
> entrega una lectura honesta y comunica cuánta confianza merece.
>
> La memoria plantea incorporarlo como trabajo futuro, una vez acumulado al
> menos un año de datos.»

---

## 8. Cierre de la defensa

Un cierre breve, que ordene lo expuesto:

> «El proyecto partió de un problema concreto: la Gerencia de TI consolidaba
> sus indicadores a mano, con reportes que llegaban con semanas de desfase y
> sin trazabilidad.
>
> El sistema automatiza ese ciclo completo, desde la carga de los archivos
> hasta la alerta al responsable del proceso. Está validado con 145 mediciones
> reales de la organización, y verificado mediante 95 pruebas automatizadas.
>
> Más allá de la automatización, el trabajo dejó visible una brecha que la
> organización no tenía cuantificada: de 44 indicadores definidos, solo 9 son
> medibles hoy. Ese diagnóstico es tan valioso como la herramienta, porque
> permite priorizar qué instrumentar primero.»

---

## 9. Errores que conviene evitar

| No hacer | En su lugar |
|---|---|
| Afirmar que está en producción | «Es un prototipo funcional, según el alcance» |
| Decir que el conector Jira opera hoy | «Está desarrollado; requiere credenciales» |
| Presentar 53 h/año como medición | «Es una estimación conservadora» |
| Ocultar el indicador que empeoró | Mencionarlo: demuestra que el sistema sirve |
| Entrar en detalles de código sin que lo pidan | Responder al nivel de la pregunta |
| Disculparse por las limitaciones | Presentarlas como decisiones de alcance |

---

## 10. Preparación logística

```bash
# Servidor de correo, para demostrar el envío de alertas
python backend/scripts/servidor_correo_prueba.py

# Servidor de la aplicación
python backend/run.py

# Verificación del estado
python backend/scripts/init_db.py --verificar
```

**Tener abierto de antemano:**

- Cuatro pestañas del navegador, una por perfil, con sesión iniciada
- La consola del servidor de correo, visible
- Un reporte PDF ya descargado, por si falla la conexión
- `python -m pytest` ejecutado, con las 95 pruebas en verde

**Si se cae la conexión a internet:** la base está en la nube, de modo que el
sistema no operaría. Conviene llevar capturas del panel, un PDF generado y la
salida de las pruebas, que se ejecutan sin conexión.
