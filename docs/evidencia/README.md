# Evidencia de respaldo

Salidas generadas por el sistema, conservadas para la defensa.

La base de datos está alojada en la nube, de modo que sin conexión a internet
el sistema no opera. Estos archivos permiten sustentar cada afirmación aunque
la demostración en vivo no sea posible.

| Archivo | Qué respalda |
|---|---|
| `reporte_procesos_criticos.pdf` | Reporte de los 11 indicadores del alcance (RF6) |
| `reporte_catalogo_completo.pdf` | Reporte de los 44 indicadores del catálogo |
| `kpis_criticos.csv` | Exportación de resultados en CSV (RF6) |
| `resultado_pruebas.txt` | 95 pruebas automatizadas en verde |
| `medicion_rendimiento.txt` | Tiempos de respuesta frente al umbral del RNF1 |
| `estado_base_datos.txt` | Registros por tabla y protección RLS de las nueve tablas |

## Regenerar

Con el servidor en ejecución:

```bash
python -m pytest -q                              > docs/evidencia/resultado_pruebas.txt
python backend/scripts/medir_rendimiento.py 3    > docs/evidencia/medicion_rendimiento.txt
python backend/scripts/init_db.py --verificar    > docs/evidencia/estado_base_datos.txt
```

Los reportes se descargan desde el panel con el botón **Reporte PDF**.

## Nota

Las pruebas automatizadas se ejecutan sin conexión a la base de datos, por lo
que `python -m pytest` funciona incluso sin internet. Es la demostración más
robusta ante una falla de conectividad.
