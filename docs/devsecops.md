# Pipeline DevSecOps

> Responsable: Arquitectura y DevSecOps · Última revisión: 2026-10-31

La seguridad se verifica en tres momentos: **antes del commit** (pre-commit), **en cada push y PR** (GitHub Actions)
y **cada semana** aunque nadie toque el código (nuevas CVEs en dependencias ya fijadas).

## Herramientas

| Herramienta | Qué detecta | Dónde corre | Amenazas |
|---|---|---|---|
| **Gitleaks** 8.30.1 | Contraseñas, llaves y tokens en el código **y en todo el historial** de git | pre-commit, CI, `dev.py scan` | T-15 |
| **Semgrep** 1.180.0 | Patrones inseguros (SAST) en Python, Dockerfile, Compose y Nginx. Reglas: `p/python`, `p/owasp-top-ten`, `p/dockerfile`, `p/docker-compose`, `p/nginx` | CI, `dev.py scan` | T-05, T-06, T-10, T-14, T-21, T-22 |
| **pip-audit** 2.10.1 | Dependencias de Python con vulnerabilidades conocidas (base de datos de PyPI/OSV) | CI (push, PR y semanal), `dev.py scan` | T-22 |
| **Dependency Review** | Dependencias vulnerables (severidad moderada o mayor) que un PR intenta agregar | CI, solo en PRs | T-22 |
| **pytest** | Pruebas del backend, incluidas las de seguridad | CI | Varias |
| **OWASP ZAP** | Escaneo dinámico (DAST) del sistema en ejecución | Local, semanas 4 y 5 (Frontend y pruebas) | T-02, T-09, T-10, T-14 |

## Workflow de CI

Archivo: [`.github/workflows/security.yml`](../.github/workflows/security.yml). Corre en cada push a `main`, en cada
PR, manualmente (*workflow_dispatch*) y los lunes a las 06:00 UTC.

| Job | Falla cuando… |
|---|---|
| Secretos (Gitleaks) | Encuentra al menos un secreto en el historial |
| SAST (Semgrep) | Encuentra al menos un hallazgo bloqueante |
| Dependencias (pip-audit) | Alguna dependencia de `backend/requirements.txt` tiene una vulnerabilidad conocida |
| Revisión de dependencias del PR | El PR agrega una dependencia con vulnerabilidad moderada o mayor |
| Pruebas del backend | Falla alguna prueba |

Los hallazgos de Gitleaks y Semgrep se publican en formato SARIF en la pestaña **Security → Code scanning** del
repositorio, donde quedan como evidencia con su historial (abierto, corregido, descartado).

**Endurecimiento del propio pipeline:**

- `permissions: contents: read` por defecto; solo los jobs que suben SARIF reciben `security-events: write`.
- Actions fijadas por **SHA de commit**, no por tag: un tag se puede mover a código malicioso, un SHA no.
- `persist-credentials: false` en el checkout: el token de GitHub no queda en disco para pasos posteriores.
- Mismas versiones de herramientas en CI y en local (`scripts/dev.py`), para que los resultados coincidan.

## Uso local

```bash
python scripts/dev.py scan
```

Corre Gitleaks, Semgrep y pip-audit en contenedores (solo requiere Docker) y deja los reportes SARIF en `reports/`.

Para bloquear secretos antes de que lleguen a un commit (una vez por clon):

```bash
pip install pre-commit
```

```bash
pre-commit install
```

## Falsos positivos

Un hallazgo solo se descarta con justificación escrita y revisada en el PR:

- **Semgrep**: comentario `# nosemgrep: <id-de-la-regla>` en la línea, junto con el motivo.
- **Gitleaks**: agregar la huella (*fingerprint*) del hallazgo a `.gitleaksignore`, junto con el motivo en el PR.

Nunca se desactiva una regla completa ni se agrega `continue-on-error` a un job para que el pipeline pase.

## Hallazgos del pipeline

Hallazgos encontrados por las herramientas automáticas. Se trasladan al registro de vulnerabilidades del proyecto.

| ID | Fecha | Herramienta | Hallazgo | Severidad | Amenaza | Corrección | Re-prueba |
|---|---|---|---|---|---|---|---|
| SAST-001 | 2026-10-31 | Semgrep `request-host-used` | `proxy/default.conf` y `proxy/snippets/proxy-backend.conf` usaban el Host enviado por el cliente en una redirección y hacia la API (Host header injection) | Media | T-05 | Servidor por defecto que responde `421`; Host fijo hacia la API | Semgrep: 0 hallazgos; `curl -H "Host: evil.example"` → `421` |
| — | 2026-10-31 | Semgrep `request-host-used` | Falso positivo: la regla coincidía con el texto de un comentario que mencionaba la variable | — | — | Se reescribió el comentario (no se usó `nosemgrep`) | Semgrep: 0 hallazgos |

Resultado del último escaneo completo (2026-10-31): Gitleaks sin fugas, Semgrep con 0 hallazgos en 208 reglas sobre
29 archivos, pip-audit sin vulnerabilidades conocidas.

## Siguientes pasos

- Escaneo de imágenes de contenedor con Trivy (paquetes del sistema operativo de las imágenes base).
- Integrar el escaneo base de ZAP en CI cuando exista la API funcional (semana 5).
- Protección de la rama `main`: exigir que el workflow pase y una revisión antes de hacer merge.
