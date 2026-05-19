# PHISHING DETECTOR

## Detector de Phishing en Correos Electrónicos

Trabajo de Fin de Grado desarrollado en la Universidad de Sevilla, Escuela Técnica Superior de Ingeniería Informática, Departamento de Lenguajes y Sistemas Informáticos.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-frontend-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![TFG](https://img.shields.io/badge/TFG-Phishing%20Detector-6B46C1)](https://github.com/JuanJavier03/phishing-detector-TFG)

Aplicación web para analizar correos electrónicos en formato `.eml`. El sistema permite subir correos individuales o lotes, ejecutar subcriterios técnicos de análisis, consultar evidencias, revisar puntuaciones MCDM/TOPSIS y exportar resultados.

> Proyecto desarrollado como Trabajo de Fin de Grado para el análisis técnico de correos electrónicos y la evaluación de riesgo mediante subcriterios y puntuación MCDM/TOPSIS.

## Índice

- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Obtención del código](#obtención-del-código)
- [Configuración](#configuración)
- [Base de datos](#base-de-datos)
- [Arranque del backend](#arranque-del-backend)
- [Arranque del frontend](#arranque-del-frontend)
- [URLs locales](#urls-locales)
- [Uso](#uso)
- [Estructura](#estructura)
- [Verificación rápida](#verificación-rápida)

## Arquitectura

La aplicación se compone de dos procesos:

| Proceso | Tecnología | Responsabilidad |
| --- | --- | --- |
| `backend` | FastAPI | API, parser de correos, enriquecimiento de subcriterios, cálculo MCDM y persistencia en PostgreSQL. |
| `frontend` | Next.js | Interfaz para subir correos, seguir jobs, consultar resultados, operar sobre lotes y revisar gráficas. |

## Requisitos

Antes de instalar el proyecto es necesario disponer de:

| Herramienta | Versión / detalle |
| --- | --- |
| Python | 3.12 |
| Node.js | 20 o superior, con `npm` |
| PostgreSQL | 16 |
| Git | Disponible desde terminal |
| Neutrino API | Credenciales `NEUTRINO_USER_ID` y `NEUTRINO_API_KEY` para los subcriterios externos |

Comprueba las versiones desde una terminal:

```bash
python --version
node --version
npm --version
psql --version
git --version
```

En Windows, Python puede estar disponible como `py -3.12` en vez de `python`.

## Obtención del código

Clona el repositorio y entra en la carpeta del proyecto:

```bash
git clone https://github.com/JuanJavier03/phishing-detector-TFG.git
cd phishing-detector-TFG
```

## Configuración

Desde la raíz del repositorio, copia los ficheros de entorno.

### Windows PowerShell

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

### Linux/macOS

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### Variables del backend

En `backend/.env` configura:

| Variable | Descripción |
| --- | --- |
| `DATABASE_URL` | Conexión a PostgreSQL. |
| `NEUTRINO_USER_ID` | Credencial de usuario para los subcriterios externos. |
| `NEUTRINO_API_KEY` | Clave de API para los subcriterios externos. |
| `MAX_UPLOAD_FILE_BYTES` | Límite de tamaño por archivo subido. |
| `MAX_BATCH_FILES` | Límite de archivos por lote. |
| `MAX_BATCH_TOTAL_BYTES` | Límite de tamaño total por lote. |
| `API_HOST` | Host de arranque de la API. |
| `API_PORT` | Puerto de arranque de la API. |
| `API_RELOAD` | Configuración de recarga de la API. |

### Variables del frontend

En `frontend/.env` configura:

| Variable | Descripción |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | URL del backend. En local debe ser `http://127.0.0.1:8000`. |

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

El comando `python -m alembic upgrade head` aplica la migración inicial final y deja preparada la base de datos.

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

## Arranque del frontend

En otra terminal:

```bash
cd frontend
npm ci
npm run dev
```

## URLs locales

| Servicio | URL |
| --- | --- |
| Frontend | `http://127.0.0.1:3000` |
| API | `http://127.0.0.1:8000` |
| Health check | `http://127.0.0.1:8000/health` |

## Uso

1. Abre `http://127.0.0.1:3000`.
2. Sube un correo individual o un lote de archivos `.eml`.
3. Selecciona los subcriterios que quieres ejecutar.
4. Espera a que el job termine.
5. Revisa el detalle del correo o del lote.
6. Consulta evidencias de subcriterios, puntuación MCDM, gráficas agregadas y errores si los hubiera.
7. Usa las acciones disponibles para reanalizar subcriterios, ejecutar pendientes, reintentar errores, recalcular MCDM, fusionar lotes o exportar resultados.

## Estructura

| Ruta | Descripción |
| --- | --- |
| `backend/api/` | API, routers, servicios, modelos y conexión a base de datos. |
| `backend/scripts/parse_emails.py` | Parseo y normalización de correos `.eml`. |
| `backend/scripts/enrichment/` | Subcriterios, transformación numérica y cálculo MCDM/TOPSIS. |
| `backend/scripts/utils/` | Utilidades compartidas de dominios, URLs, cabeceras, caché y normalización. |
| `backend/alembic/versions/20260318_0001_initial_schema.py` | Migración inicial con el esquema final. |
| `frontend/src/app/` | Rutas de la interfaz. |
| `frontend/src/components/` | Pantallas y componentes reutilizables. |
| `frontend/src/lib/` | Cliente API, tipos, formateo y polling. |

## Verificación rápida

| Problema | Revisión |
| --- | --- |
| La API no arranca | Revisa `backend/.env`, confirma que PostgreSQL está iniciado y ejecuta `python -m alembic upgrade head` desde `backend`. |
| La migración falla con error de conexión | Comprueba que `DATABASE_URL` coincide con el usuario, contraseña, host, puerto y base de datos creados. |
| El frontend no conecta | Revisa `frontend/.env` y confirma que el backend está disponible en `http://127.0.0.1:8000`. |
| Faltan resultados externos | Comprueba las credenciales de Neutrino y los flags `IPREP_ALLOW_HTTP`, `DOMAINREP_ALLOW_HTTP`, `DOMAINIP_ALLOW_HTTP`, `DOMAINAGE_ALLOW_HTTP` y `CAPTCHA_ALLOW_HTTP`. |
