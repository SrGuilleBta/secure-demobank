# secure-demobank

Billetera digital simulada, construida con prácticas de desarrollo de software seguro.
Proyecto Integrador Académico (PIA) de *Desarrollo de Software Seguro*, FCFM.

## Arquitectura en una línea

Navegador → **Nginx** (cabeceras, rate limiting) → **FastAPI** (red interna) → **PostgreSQL** (red interna).
Solo el proxy publica puertos, y solo en `127.0.0.1`. Detalles en [docs/arquitectura.md](docs/arquitectura.md).

## Cómo arrancar el proyecto

### Requisitos

- **Docker Desktop** instalado y **abierto** (el ícono de la ballena debe indicar que está corriendo)
- **Python 3.12** o superior
- **Git**

> **Clona el repo en un disco interno (NTFS, ext4, APFS), no en una USB.** Docker Desktop no comparte unidades
> removibles con su máquina virtual, y FAT32 no guarda dueños de archivos (git responde con "dubious ownership").

### Pasos

1. Clona el repositorio y entra a la carpeta:

   ```bash
   git clone https://github.com/SrGuilleBta/secure-demobank
   ```

   ```bash
   cd secure-demobank
   ```

2. Levanta todo con un solo comando:

   ```bash
   python scripts/dev.py up
   ```

3. Abre el navegador:

   | Qué | Dirección |
   |---|---|
   | Aplicación | <http://localhost:8080> |
   | Estado de la API | <http://localhost:8080/api/health> (debe responder `{"status":"ok"}`) |
   | Documentación de la API | <http://localhost:8080/api/docs> (solo con `APP_ENV=development`, que es el valor por defecto en local) |

La primera vez tarda unos minutos porque descarga las imágenes de Docker. Qué hace `up` por ti:

1. Genera contraseñas aleatorias en `secrets/` (una por cada clon; **nunca se suben a git**).
2. Crea el archivo `.env` a partir de `.env.example`.
3. Construye y levanta los tres contenedores: `proxy`, `backend` y `db`.
4. Espera a que la API responda y te avisa.

### Comandos del día a día

| Comando | Qué hace |
|---|---|
| `python scripts/dev.py up` | Levanta el stack (también reconstruye el backend si cambió) |
| `python scripts/dev.py down` | Detiene el stack y **conserva** los datos |
| `python scripts/dev.py reset` | Detiene el stack y **borra la base de datos** (pide confirmación) |
| `python scripts/dev.py logs` | Sigue los logs de todos los servicios (Ctrl+C para salir) |
| `python scripts/dev.py setup` | Solo genera secretos y `.env`, sin levantar nada (nunca sobrescribe) |
| `python scripts/dev.py scan` | Gitleaks, Semgrep y pip-audit, igual que en el CI |

### Después de cambiar código

| Qué cambiaste | Qué hacer |
|---|---|
| Código del backend (`backend/`) | `python scripts/dev.py up` (reconstruye la imagen) |
| Configuración del proxy (`proxy/`) | `docker compose restart proxy` |
| Archivos del frontend (`frontend/public/`) | Nada: solo recarga la página |
| Contraseñas (`secrets/`) o scripts de `db/init/` | `python scripts/dev.py reset` y luego `up` (la base de datos solo lee esos datos al crearse) |

### Pruebas del backend

```bash
cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt && .venv/Scripts/pytest
```

(En Linux/macOS, usa `.venv/bin/` en lugar de `.venv/Scripts/`.)

### Problemas comunes

| Síntoma | Causa y solución |
|---|---|
| `error during connect` o `cannot connect to the Docker daemon` | Docker Desktop no está abierto. Ábrelo, espera a que arranque y repite el comando. |
| `invalid mount config ... bind source path does not exist` | El repo está en una unidad que Docker no comparte (por ejemplo una USB). Muévelo a un disco interno. |
| `port is already allocated` o `address already in use` | El puerto 8080 está ocupado. Cambia `HTTP_PORT` en `.env` (por ejemplo a `8081`) y repite `up`. |
| `password authentication failed` en los logs de `backend` | Borraste o regeneraste `secrets/` con la base de datos ya creada. Corre `python scripts/dev.py reset` y luego `up`. |
| El stack "no respondió a tiempo" | Revisa con `python scripts/dev.py logs` cuál de los tres servicios falla. |
| `/api/docs` responde 404 | `APP_ENV` no es `development`. Revisa tu `.env`. |

## Estructura

```
backend/        API FastAPI (app/, tests/, Dockerfile)
frontend/       Frontend (libre elección, preferentemente React; por ahora un marcador estático en public/)
proxy/          Configuración de Nginx: cabeceras de seguridad, rate limiting
db/init/        Creación de roles de PostgreSQL con mínimo privilegio
scripts/dev.py  Arranque, reinicio y escaneos locales
docs/           Arquitectura, modelo de amenazas y pipeline DevSecOps
.github/        Workflow de seguridad
```

## Documentación de seguridad

| Documento | Contenido |
|---|---|
| [docs/guia-equipo.md](docs/guia-equipo.md) | **Empieza aquí si eres del equipo:** dónde estamos, cómo trabajamos y qué le toca a cada rol |
| [docs/arquitectura.md](docs/arquitectura.md) | Componentes, límites de confianza, flujos de datos, activos, decisiones de diseño seguro y su verificación |
| [docs/modelo-amenazas.md](docs/modelo-amenazas.md) | STRIDE por elemento, 24 amenazas con riesgo, mitigación, responsable y prueba; casos de abuso; riesgos aceptados |
| [docs/devsecops.md](docs/devsecops.md) | Pipeline de CI, herramientas, manejo de falsos positivos y hallazgos del pipeline |
