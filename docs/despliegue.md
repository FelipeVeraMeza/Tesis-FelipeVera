# Despliegue en Railway

El sistema se publica como una sola aplicación: el servidor Flask entrega tanto
la API como los archivos de la interfaz, de modo que basta una única URL.

La base de datos ya está alojada en Supabase, por lo que no requiere despliegue
adicional.

---

## 1. Preparación

Estos archivos ya están en el repositorio:

| Archivo | Función |
|---|---|
| `Procfile` | Comando de arranque del servidor |
| `railway.json` | Configuración de compilación y reinicio |
| `runtime.txt` | Versión de Python |
| `requirements.txt` | Dependencias (copia de `backend/requirements.txt`) |

---

## 2. Crear el proyecto

1. Entrar a <https://railway.app> e iniciar sesión con la cuenta de GitHub.
2. **New Project** → **Deploy from GitHub repo**.
3. Seleccionar el repositorio `Tesis-FelipeVera`.

Railway detecta el proyecto Python y comienza la compilación. El primer
despliegue fallará hasta que se definan las variables de entorno.

---

## 3. Variables de entorno

En el panel del proyecto: **Variables** → **New Variable**.

### Obligatorias

| Variable | Valor |
|---|---|
| `SUPABASE_URL` | `https://<proyecto>.supabase.co` |
| `SUPABASE_SECRET_KEY` | La clave de servicio de Supabase |
| `SUPABASE_PUBLISHABLE_KEY` | La clave pública de Supabase |
| `SECRET_KEY` | Una cadena propia y aleatoria |
| `ENTORNO` | `produccion` |

`SECRET_KEY` firma los tokens de sesión. Debe ser un valor propio: el sistema
se niega a arrancar en producción si conserva el valor por defecto.

Para generarla:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Opcionales

| Variable | Para qué sirve |
|---|---|
| `SMTP_HOST`, `SMTP_PUERTO`, `SMTP_USUARIO`, `SMTP_CLAVE` | Envío efectivo de las alertas |
| `SMTP_REMITENTE`, `SMTP_TLS`, `SMTP_SSL` | Configuración del correo |
| `DOMINIO_CORREO`, `CORREO_GERENCIA` | Casillas de los responsables |
| `JIRA_URL`, `JIRA_USUARIO`, `JIRA_TOKEN` | Extracción automática desde Jira |
| `SUPABASE_DB_PASSWORD` | Solo si se ejecutan migraciones desde el servidor |

Sin las variables de correo, las notificaciones se registran como simuladas.
Sin las de Jira, la carga se realiza por archivo.

**No definir** `SUPABASE_DB_PASSWORD` salvo que sea necesario: la aplicación no
la requiere para operar.

---

## 4. Publicar la aplicación

En **Settings** → **Networking** → **Generate Domain**.

Railway asigna una dirección del tipo
`https://<nombre>.up.railway.app`.

---

## 5. Verificación

```bash
curl https://<dominio>/api/salud
```

Debe responder:

```json
{"conectado": true, "esquema_creado": true, "url": "https://..."}
```

Luego, abrir el dominio en el navegador e iniciar sesión.

---

## 6. Consideraciones

### La base de datos ya existe

El esquema y los datos están en Supabase, de modo que el despliegue no requiere
migraciones. Si fuera necesario recrearlos, se ejecuta desde un equipo local:

```bash
python backend/scripts/init_db.py
```

### Acceso público

El sistema queda accesible desde internet con los usuarios de prueba
documentados. Para una defensa es lo adecuado, pero conviene tenerlo presente:
cualquiera con la dirección puede ingresar.

Si más adelante se requiere restringirlo, basta con cambiar las contraseñas
mediante el script de inicialización.

### Row Level Security

La protección de la base de datos no se altera con el despliegue: las tablas
siguen siendo inaccesibles con la clave pública, y solo la capa de aplicación
—que usa la clave de servicio— puede consultarlas.

### Actualizaciones

Railway vuelve a desplegar automáticamente con cada `git push` a la rama `main`.

---

## 7. Ejecución local

El despliegue no altera el funcionamiento local. Con el archivo `.env`
presente, el sistema opera igual que antes:

```bash
python backend/run.py
```

La diferencia está en la variable `ENTORNO`: sin definirla, el sistema asume
desarrollo y mantiene activo el modo de depuración.

---

## 8. Problemas frecuentes

**El despliegue falla al arrancar**
Revisar los registros en Railway. Si el mensaje menciona variables faltantes,
verificar que `SUPABASE_URL` y `SUPABASE_SECRET_KEY` estén definidas.

**Responde «Defina SECRET_KEY…»**
Falta esa variable, o conserva el valor por defecto. Generar una propia.

**El panel carga pero no muestra indicadores**
Comprobar `/api/salud`. Si `esquema_creado` es `false`, la base no tiene las
tablas: ejecutar la inicialización desde un equipo local.

**Las alertas no envían correo**
Es el comportamiento previsto sin un servidor SMTP configurado: la
notificación se registra y se informa como simulada.
