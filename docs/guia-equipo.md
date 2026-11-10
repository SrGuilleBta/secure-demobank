# Guía del equipo

Qué llevamos, cómo vamos a trabajar y qué le toca a cada quien. Léete primero la sección 1 y 2, y después solo la
tuya (sección 4).

## 1. Dónde estamos

**Secure DemoBank** es una billetera digital simulada: los usuarios se registran, ven su saldo, transfieren dinero
ficticio a otros usuarios y revisan su historial. Un administrador gestiona usuarios y consulta la bitácora.

**Stack:** FastAPI (Python) + PostgreSQL + Nginx como proxy. El frontend es React (Vite).

### Ya está hecho

| Qué | Dónde |
|---|---|
| Stack completo que arranca con un comando (proxy, API, base de datos) | [README.md](../README.md) |
| Redes internas, contenedores sin root, secretos generados, roles de BD con mínimo privilegio | [arquitectura.md](arquitectura.md) |
| Proxy con cabeceras de seguridad, CSP estricta, rate limiting y límites de tamaño | `proxy/` |
| Modelo de amenazas STRIDE con 24 amenazas, casos de abuso y riesgos aceptados | [modelo-amenazas.md](modelo-amenazas.md) |
| CI de seguridad (Gitleaks, Semgrep, pip-audit, npm audit, pruebas) | [devsecops.md](devsecops.md) |
| API completa: registro, login, sesiones, cuenta, transferencias, panel de administrador y bitácora (63 pruebas) | `backend/` |
| Frontend React (Vite) compilado dentro de la imagen del proxy, con pantalla inicial | `frontend/` |

### Falta por construir

- Las pantallas del frontend (registro, login, saldo, transferencias, historial y administrador).
- Las pruebas dinámicas con ZAP, el registro de vulnerabilidades y la presentación final.
- Decisión ya tomada: las sesiones van en cookie con token CSRF (D-16) y las tablas se crean con un script SQL (D-17).

## 2. Cómo trabajamos

1. **Arranca el proyecto** siguiendo el [README](../README.md). Necesitas Docker Desktop abierto y el repo en un disco
   interno, no en una USB.
2. **Una rama por tarea**, con el nombre que quieras, y **un pull request** para juntarla con `main`. Esta es una
   propuesta; si el equipo prefiere otro flujo, se ajusta.
3. **El CI debe quedar en verde** antes de juntar un PR. Corre Gitleaks, Semgrep, pip-audit, npm audit y las pruebas. Puedes
   correr los escaneos antes de subir: `python scripts/dev.py scan`.
4. **Nunca subas secretos.** Las contraseñas viven en `secrets/` y `.env`, que están en `.gitignore`. Cada quien
   genera los suyos al arrancar.
5. **Cada decisión o hallazgo se documenta con los IDs del proyecto:** `T-xx` (amenazas), `D-xx` (decisiones de
   diseño), `A-xx` (activos) y `RA-xx` (riesgos aceptados). Con eso se arma la cadena que pide el PDF:
   **amenaza → riesgo → mitigación → implementación → prueba → resultado**.
6. **Las pruebas de seguridad se hacen solo sobre nuestro sistema local**, nunca contra sitios o servicios ajenos
   (lo exige el PDF).

### Definición de "terminado" para cualquier tarea

- [ ] Funciona al arrancar con `python scripts/dev.py up`.
- [ ] Tiene pruebas, incluida al menos una de seguridad cuando aplica (el caso de abuso que corresponde).
- [ ] `python scripts/dev.py scan` no reporta hallazgos nuevos.
- [ ] Se actualizó [modelo-amenazas.md](modelo-amenazas.md): la columna Verificación de la amenaza y el resumen de
      la sección 7.
- [ ] Hay evidencia guardada (captura, salida de un comando o resultado de una prueba). Sugerencia: carpeta
      `docs/evidencia/` con nombres como `T-07-monto-negativo.png`.

## 3. Reparto y entregables

| Rol | Responsable de | Amenazas que le tocan |
|---|---|---|
| **Arquitectura y DevSecOps** | Repo, Docker Compose, arquitectura, modelo de amenazas, CI, criptografía | T-03 (borde), T-04, T-05, T-12, T-15, T-16, T-18, T-21, T-22 |
| **Backend y seguridad de acceso** | API, autenticación, autorización, validación, bitácora | T-01, T-02, T-03 (por cuenta), T-06, T-07, T-08, T-11, T-13, T-14, T-17, T-19, T-20, T-24 |
| **Frontend y pruebas de seguridad** | Interfaz, XSS/CSRF, cabeceras, ZAP | T-09, T-10, T-23 (verificación) |
| **Documentación, requisitos y gestión** | Alcance, requisitos, matriz de roles, registro de vulnerabilidades, presentación | T-20 (matriz de roles) |

El PDF del PIA organiza el trabajo en cinco semanas, con dos entregables:

| Semana | Tema | Entregable |
|---|---|---|
| 1 | Definición del sistema y requisitos de seguridad | **Entregable 1** |
| 2 | Diseño seguro y modelo de amenazas | **Entregable 1** |
| 3 | Implementación segura | **Entregable 2** |
| 4 | Verificación y análisis de seguridad | **Entregable 2** |
| 5 | Integración, aseguramiento y versión final | **Entregable 2** |

## 4. Qué le toca a cada quien

### 4.1 Arquitectura y DevSecOps

**Ya hecho:** todo lo de la sección 1.

**Pendiente**

- [x] **Esquema de la base de datos** (`db/schema.sql`, cargado por el rol `demobank_migrator`) y **hash Argon2id**
      (`backend/app/security.py`). Hechos.
- [ ] **Escaneo de imágenes** con Trivy en el CI (T-22).
- [ ] **Protección de la rama `main`**: exigir CI en verde y una revisión antes de juntar un PR.
- [ ] **Revisar los PRs del equipo** con ojos de seguridad, y mantener al día el modelo de amenazas.
- [ ] **Semana 5:** revisar el uso de criptografía, las dependencias finales, y dejar el CI listo para la demostración.

**Archivos:** `docker-compose.yml`, `proxy/`, `db/init/`, `scripts/dev.py`, `.github/`, `docs/`.

### 4.2 Backend y seguridad de acceso

**Estado:** la API ya está construida y probada (63 pruebas, 57 de ellas contra un PostgreSQL real). Esta sección
explica cómo está armada y cómo seguir extendiéndola.

**Cómo está armada** (`backend/app/`)

| Archivo | Qué hace |
|---|---|
| `main.py` | Crea la app, registra los routers y los manejadores de errores (500 genérico; 422 sin devolver lo enviado) |
| `routers/auth.py` | Registro, login (con bloqueo de cuenta) y logout |
| `routers/accounts.py` | `/api/me` y `/api/account` |
| `routers/transfers.py` | Crear, listar y consultar transferencias |
| `routers/admin.py` | Usuarios y bitácora, solo para administradores |
| `deps.py` | Quién es el usuario de la sesión, exigir token CSRF y exigir rol administrador |
| `security.py` | Argon2id, generación y hash de tokens |
| `schemas.py` | Validación estricta de entradas y forma de las respuestas |
| `audit.py` | Escritura en la bitácora |
| `config.py`, `db.py` | Configuración, secretos y conexión |

**Endpoints** (todos bajo `/api`; el frontend los usa sin CORS, por el mismo origen)

| Método y ruta | Quién | Qué hace |
|---|---|---|
| `POST /auth/register` | Cualquiera | Crea una cuenta de cliente con saldo inicial de 100.000 centavos |
| `POST /auth/login` | Cualquiera | Devuelve `username`, `role` y `csrf_token`, y pone la cookie de sesión |
| `POST /auth/logout` | Con sesión + CSRF | Cierra la sesión en el servidor |
| `GET /me`, `GET /account` | Con sesión | Datos del usuario y saldo |
| `POST /transfers` | Con sesión + CSRF | Transfiere: `to_username`, `amount_cents` (entero), `concept`, `idempotency_key` (UUID) |
| `GET /transfers?page=&page_size=` | Con sesión | Historial propio, máximo 50 por página |
| `GET /transfers/{id}` | Con sesión | Una transferencia propia; si es ajena, `404` |
| `GET /admin/users`, `GET /admin/audit` | Administrador | Usuarios y bitácora |

**Reglas para el frontend.** Guardar el `csrf_token` que devuelve el login (en memoria, no en `localStorage`) y enviarlo
en la cabecera `X-CSRF-Token` en cada `POST`. La cookie de sesión la maneja el navegador. Cada transferencia nueva lleva
una `idempotency_key` nueva (`crypto.randomUUID()`); si se reintenta la misma petición, se reutiliza la misma.

**Cómo extenderla**

- **Un endpoint nuevo:** agrégalo en un router, valida la entrada con un esquema de `schemas.py` (siempre `extra="forbid"`),
  usa `Depends(get_current_user)` o `Depends(require_csrf)` si cambia datos, filtra por el dueño autenticado y registra
  en la bitácora si es un evento de seguridad.
- **Consultas SQL:** siempre con parámetros (`:nombre`), nunca armando texto. Si una consulta necesita unir tablas,
  créale una vista en `db/schema.sql` (como `transfer_details`) y consúltala con texto fijo.
- **Cambiar las tablas:** edita `db/schema.sql` y corre `python scripts/dev.py reset` y luego `up`.
- **Un administrador:** regístralo desde la aplicación y luego `python scripts/dev.py admin <usuario>`.
- **Una librería:** fija su versión en `backend/requirements.txt` (el CI corre `pip-audit`).
- **Un secreto nuevo:** `PASSWORD_SECRETS`/`KEY_SECRETS` en `scripts/dev.py`, `secrets:` en `docker-compose.yml` y `Settings`.

**Correr las pruebas:** `python scripts/dev.py test` (levanta una base de datos desechable, corre pytest y la borra).
Sin Docker, `pytest` corre solo las pruebas que no necesitan base de datos y salta el resto.

**Pendiente (opcional)**

- [ ] `statement_timeout` en la conexión a la base de datos (T-19).
- [ ] Lista de contraseñas comunes y MFA (T-01): fuera del alcance acordado; documentado en el modelo de amenazas.

### 4.3 Frontend y pruebas de seguridad

**Frontend:** React + Vite, ya configurado en `frontend/`. Cómo correrlo y trabajar en él:
[frontend/README.md](../frontend/README.md). Lo esencial:

- El navegador solo habla con el proxy (`http://localhost:8080`). **Frontend y API comparten origen**: no hace falta
  CORS.
- La API vive bajo `/api/`. Todo lo demás lo sirve el proxy con el build de React (se compila dentro de su imagen).
- **La CSP no permite JavaScript ni CSS escritos dentro del HTML.** Todo debe ir en archivos propios. Si una
  librería lo necesita, se documenta y se ajusta la política en `proxy/default.conf`.
- Para desarrollar con recarga instantánea: `npm run dev` en `frontend/` (puerto 5173). Ya manda `/api` al proxy.
- Para ver el build final dentro del stack: `python scripts/dev.py up` (reconstruye la imagen del proxy).

**Tareas de interfaz**

- [ ] Pantallas: registro, login, saldo, transferencia, historial y panel de administrador.
- [ ] **Nunca insertar HTML crudo** (en React, no usar `dangerouslySetInnerHTML`); el concepto de una transferencia
      y los nombres se muestran como texto (T-10).
- [ ] No guardar tokens ni datos sensibles en `localStorage`.
- [ ] Enviar el token anti-CSRF en cada petición que cambie datos (T-09), de acuerdo con Backend.
- [ ] No mostrar al usuario trazas ni mensajes internos de error (T-14).

**Pruebas de seguridad (semanas 4 y 5)**

- [ ] **OWASP ZAP** apuntado a `http://localhost:8080`; importar `http://localhost:8080/api/openapi.json` (solo existe
      con `APP_ENV=development`, que es el valor por defecto en local). Guardar los reportes como evidencia.
- [ ] **Casos de prueba de seguridad** a partir de los casos de abuso CA-01 a CA-09
      ([modelo-amenazas.md](modelo-amenazas.md), sección 5): para cada uno, qué se hace, qué se espera y qué
      se obtuvo.
- [ ] **Verificar las cabeceras y la CSP** en el navegador (consola, pestaña Red): ya están en el proxy.
- [ ] Cada falla encontrada pasa al registro de vulnerabilidades (ver 4.4). Cuando se corrija, **repetir la prueba**
      y anotar el resultado: el PDF lo pide explícitamente.
- [ ] Probar **solo** sobre el sistema local.

### 4.4 Documentación, requisitos y gestión

**Pendiente**

- [ ] **Confirmar con el docente que el proyecto está aprobado** (el PDF dice que debe aprobarse antes).
- [ ] **Definición y alcance del sistema**: problema que resuelve, objetivo y alcance. Hay un borrador en la sección 1
      de [arquitectura.md](arquitectura.md).
- [ ] **Requisitos funcionales y de seguridad.** El PDF pide, entre otros: autenticación y autorización,
      validación de entradas, manejo de errores, no exponer información sensible, análisis estático y dinámico,
      registro de eventos y uso de criptografía.
- [ ] **Matriz de roles:** qué puede hacer cada rol (`cliente`, `administrador`) en cada operación. **Los dos roles
      son un supuesto mío; hay que confirmarlos o cambiarlos** y avisar a Backend (T-20).
- [ ] **Cronograma y distribución de responsabilidades**, y seguimiento de las tareas del equipo.
- [ ] **Registro de vulnerabilidades** (ver plantilla abajo), alimentado por Semgrep, ZAP y las pruebas manuales.
      Los dos primeros hallazgos ya están en la sección "Hallazgos del pipeline" de [devsecops.md](devsecops.md).
- [ ] **Trazabilidad** amenaza → riesgo → mitigación → implementación → prueba → resultado. El ejemplo de T-05 en
      [modelo-amenazas.md](modelo-amenazas.md) (sección 8) muestra el formato.
- [ ] **Documento técnico final** juntando todo.
- [ ] **Presentación, video de demostración y declaración de originalidad e integridad académica.** Si se usó IA,
      declararlo, y que cada quien pueda explicar y defender lo que presenta (lo exige el PDF).

**Plantilla del registro de vulnerabilidades**

| ID | Fecha | Cómo se encontró | Descripción | Severidad | Amenaza | Causa | Corrección | Re-prueba | Resultado |
|---|---|---|---|---|---|---|---|---|---|
| V-01 | | | | | T-xx | | | | |

**La presentación final debe incluir** (lista del PDF): problema, objetivo y alcance, arquitectura, activos,
requisitos de seguridad, modelo de amenazas, principales amenazas, mitigaciones, mecanismos implementados,
demostración, herramientas de verificación, vulnerabilidades encontradas, correcciones, evidencia de las pruebas
finales y conclusiones.

## 5. Dónde está cada cosa

```
backend/app/        main.py, routers/ (endpoints), security.py, deps.py, schemas.py, config.py, db.py
backend/tests/      Pruebas del backend (pytest)
frontend/           Frontend
proxy/              Nginx: cabeceras, CSP, rate limiting, límites
db/init/            Roles de PostgreSQL
scripts/dev.py      Arranque, reinicio y escaneos
docs/               arquitectura.md, modelo-amenazas.md, devsecops.md y esta guía
.github/            CI de seguridad
```
