# Phishing Detector

Aplicación web para analizar correos electrónicos en formato `.eml`. El sistema permite subir correos individuales o lotes, ejecutar subcriterios técnicos de análisis, consultar evidencias, revisar puntuaciones MCDM/TOPSIS y exportar resultados.

La aplicación se compone de dos procesos:

- `backend`: API FastAPI, parser de correos, enriquecimiento de subcriterios, cálculo MCDM y persistencia en PostgreSQL.
- `frontend`: interfaz Next.js para subir correos, seguir jobs, consultar resultados, operar sobre lotes y revisar gráficas.

## Requisitos

Antes de instalar el proyecto es necesario disponer de:

- Python 3.12.
- Node.js 20 o superior, con `npm`.
- PostgreSQL 16.
- Credenciales de Neutrino API para los subcriterios externos: `NEUTRINO_USER_ID` y `NEUTRINO_API_KEY`.

Comprueba las versiones desde una terminal:

```bash
python --version
node --version
npm --version
psql --version
```

En Windows, Python puede estar disponible como `py -3.12` en vez de `python`.

## Configuración

Desde la raíz del repositorio, copia los ficheros de entorno:

Windows PowerShell:

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

Linux/macOS:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

En `backend/.env` configura:

- `DATABASE_URL`: conexión a PostgreSQL.
- `NEUTRINO_USER_ID` y `NEUTRINO_API_KEY`: credenciales para los subcriterios externos.
- `MAX_UPLOAD_FILE_BYTES`, `MAX_BATCH_FILES` y `MAX_BATCH_TOTAL_BYTES`: límites de subida.
- `API_HOST`, `API_PORT` y `API_RELOAD`: configuración de arranque de la API.

En `frontend/.env` configura:

- `NEXT_PUBLIC_API_BASE_URL`: URL del backend. En local debe ser `http://127.0.0.1:8000`.

## Base de datos

Crea el usuario y la base de datos indicados en `backend/.env.example`.

### Windows

Abre PowerShell y entra en `psql` con el usuario administrador de PostgreSQL:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres
```

Ejecuta:

```sql
CREATE USER app_user WITH PASSWORD 'app_password';
CREATE DATABASE phishing_detector OWNER app_user;
\q
```

### Linux

En Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql
sudo -u postgres psql
```

Ejecuta:

```sql
CREATE USER app_user WITH PASSWORD 'app_password';
CREATE DATABASE phishing_detector OWNER app_user;
\q
```

### macOS

Con Homebrew:

```bash
brew install postgresql@16
brew services start postgresql@16
psql -d postgres
```

Ejecuta:

```sql
CREATE USER app_user WITH PASSWORD 'app_password';
CREATE DATABASE phishing_detector OWNER app_user;
\q
```

## Arranque del backend

### Windows PowerShell

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m alembic upgrade head
python scripts/run_api.py
```

Si PowerShell bloquea la activación del entorno virtual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Linux/macOS

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m alembic upgrade head
python scripts/run_api.py
```

El comando `python -m alembic upgrade head` aplica la migración inicial final y deja preparada la base de datos.

## Arranque del frontend

En otra terminal:

```bash
cd frontend
npm ci
npm run dev
```

## URLs locales

- Frontend: `http://127.0.0.1:3000`
- API: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/health`

## Uso

1. Abre `http://127.0.0.1:3000`.
2. Sube un correo individual o un lote de archivos `.eml`.
3. Selecciona los subcriterios que quieres ejecutar.
4. Espera a que el job termine.
5. Revisa el detalle del correo o del lote.
6. Consulta evidencias de subcriterios, puntuación MCDM, gráficas agregadas y errores si los hubiera.
7. Usa las acciones disponibles para reanalizar subcriterios, ejecutar pendientes, reintentar errores, recalcular MCDM, fusionar lotes o exportar resultados.

## Estructura

- `backend/api/`: API, routers, servicios, modelos y conexión a base de datos.
- `backend/scripts/parse_emails.py`: parseo y normalización de correos `.eml`.
- `backend/scripts/enrichment/`: subcriterios, transformación numérica y cálculo MCDM/TOPSIS.
- `backend/scripts/utils/`: utilidades compartidas de dominios, URLs, cabeceras, caché y normalización.
- `backend/alembic/versions/0001_initial_schema.py`: migración inicial con el esquema final.
- `frontend/src/app/`: rutas de la interfaz.
- `frontend/src/components/`: pantallas y componentes reutilizables.
- `frontend/src/lib/`: cliente API, tipos, formateo y polling.

## Verificación rápida

- Si la API no arranca, revisa `backend/.env`, confirma que PostgreSQL está iniciado y ejecuta `python -m alembic upgrade head` desde `backend`.
- Si la migración falla con error de conexión, comprueba que `DATABASE_URL` coincide con el usuario, contraseña, host, puerto y base de datos creados.
- Si el frontend no conecta, revisa `frontend/.env` y confirma que el backend está disponible en `http://127.0.0.1:8000`.
- Si faltan resultados externos, comprueba las credenciales de Neutrino y los flags `IPREP_ALLOW_HTTP`, `DOMAINREP_ALLOW_HTTP`, `DOMAINIP_ALLOW_HTTP`, `DOMAINAGE_ALLOW_HTTP` y `CAPTCHA_ALLOW_HTTP`.
