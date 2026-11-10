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
| API mínima: solo `/api/health`, configuración y una prueba | `backend/` |

### Falta por construir

- Toda la lógica del banco: registro, login, cuentas, transferencias, historial, panel de administrador.
- El frontend.
- Las pruebas de seguridad (ZAP y casos de prueba), el registro de vulnerabilidades y la presentación final.

La mayor parte de las amenazas del modelo (T-01, T-02, T-07, T-08, T-09, T-11, T-13, T-17, T-20) están **pendientes
porque dependen de esa lógica**: son las que se implementan en la semana 3.

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

- [ ] **Servicio de migraciones.** Un servicio de un solo uso en `docker-compose.yml` que corra las migraciones con
      el rol `demobank_migrator`, y del que dependa `backend`. El backend ya no podrá crear tablas con su propio
      usuario; esto es intencional (D-07). Coordinar con Backend la herramienta (Alembic es la opción natural).
- [ ] **Hash de contraseñas con Argon2id** (el extra de criptografía): una función de hash y verificación que use
      Backend, con parámetros documentados y una prueba (T-01). Si prefieres que Backend lo haga, acordarlo.
- [ ] **Escaneo de imágenes** con Trivy en el CI (T-22).
- [ ] **Protección de la rama `main`**: exigir CI en verde y una revisión antes de juntar un PR.
- [ ] **Revisar los PRs del equipo** con ojos de seguridad, y mantener al día el modelo de amenazas.
- [ ] **Semana 5:** revisar el uso de criptografía, las dependencias finales, y dejar el CI listo para la demostración.

**Archivos:** `docker-compose.yml`, `proxy/`, `db/init/`, `scripts/dev.py`, `.github/`, `docs/`.

### 4.2 Backend y seguridad de acceso

**Punto de partida:** `backend/app/` ya tiene `main.py` (la app y `/api/health`), `config.py` (configuración y
secretos) y `db.py` (conexión a la base de datos). Las pruebas están en `backend/tests/`.

**Lo que tienes que saber de la infraestructura**

- La API se conecta como `demobank_app`: **solo puede leer y escribir datos**, no crear ni borrar tablas. Las tablas
  las crea el rol `demobank_migrator` (esquema `app`) y la API recibe permisos automáticamente.
- Los secretos se leen con `get_settings()` (`backend/app/config.py`) y son `SecretStr`. La llave para firmar
  sesiones o tokens ya existe: `settings.app_secret_key`. Para agregar un secreto nuevo hay que tocar
  `PASSWORD_SECRETS`/`KEY_SECRETS` en `scripts/dev.py`, `secrets:` en `docker-compose.yml` y `Settings`.
- Todo llega por el proxy bajo `/api/`. Tu API ve la IP real del cliente (el proxy sobrescribe `X-Forwarded-For`).
- Para agregar una librería: fija su versión en `backend/requirements.txt`. El CI corre `pip-audit` sobre ese archivo
  y falla si hay vulnerabilidades conocidas.

**Tareas** (en el orden sugerido)

- [ ] **Modelo de datos y migraciones:** usuarios, cuentas, transferencias y bitácora. Dinero en **centavos
      (enteros)**, nunca `float`; `CHECK (saldo >= 0)` en la tabla.
- [ ] **Registro y login (T-01, T-17):** contraseñas con Argon2id, política de contraseñas, mensajes genéricos y
      tiempo de respuesta constante aunque el usuario no exista.
- [ ] **Sesiones (T-02):** decisión pendiente, **sesión en cookie `HttpOnly; SameSite=Strict` con token anti-CSRF**
      (recomendada, más difícil de robar con XSS) o JWT. Documentar la decisión como un `D-xx` nuevo en
      [arquitectura.md](arquitectura.md). Expiración, cierre de sesión que invalida en el servidor.
- [ ] **Autorización (T-20, T-13):** denegar por defecto; el rol sale del servidor, nunca del cuerpo de la petición;
      **cada consulta filtra por el dueño autenticado**, no solo por ID; responder `404` y no `403` para recursos
      ajenos.
- [ ] **Validación (T-07):** esquemas Pydantic con `extra="forbid"` y rangos (`gt=0`, monto máximo). La cuenta de
      origen de una transferencia **sale de la sesión**, nunca del cuerpo.
- [ ] **Transferencias (T-08):** una sola transacción con `SELECT ... FOR UPDATE` sobre ambas cuentas, en orden
      fijo para evitar bloqueos mutuos, y llave de idempotencia contra reenvíos.
- [ ] **Bitácora de auditoría (T-11):** login correcto y fallido, transferencias y cambios de rol, con usuario,
      acción, recurso, IP y fecha del servidor. Tabla *append-only*: en su migración, `REVOKE UPDATE, DELETE` a
      `demobank_app`.
- [ ] **Bloqueo por cuenta (T-03):** bloqueo temporal tras N intentos fallidos (el proxy ya limita por IP).
- [ ] **Errores y logs (T-14, T-24):** manejador global que responda genérico y deje el detalle en el log; nunca
      registrar contraseñas, tokens ni datos completos.
- [ ] **Paginación (T-19):** tamaño de página máximo.
- [ ] **Una prueba por caso de abuso** que te toque (CA-01, CA-02, CA-03, CA-05, CA-07 en
      [modelo-amenazas.md](modelo-amenazas.md)).

**Correr las pruebas:** ver el [README](../README.md#pruebas-del-backend).

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

## 5. Decisiones abiertas

| Decisión | Quién | Mi recomendación |
|---|---|---|
| ¿Sesión en cookie o JWT? | Backend | Cookie `HttpOnly; SameSite=Strict` con token anti-CSRF |
| ¿Roles `cliente` y `administrador`, y qué puede hacer cada uno? | Docs, con Backend | Empezar con esos dos |
| ¿Quién implementa el hash Argon2id? | Arquitectura y Backend | Arquitectura escribe la función, Backend la usa |
| ¿Herramienta de migraciones? | Arquitectura y Backend | Alembic |
| ¿Está aprobado el proyecto por el docente? | Docs | Confirmarlo cuanto antes |

## 6. Dónde está cada cosa

```
backend/app/        main.py (la API), config.py (secretos), db.py (conexión)
backend/tests/      Pruebas del backend (pytest)
frontend/           Frontend
proxy/              Nginx: cabeceras, CSP, rate limiting, límites
db/init/            Roles de PostgreSQL
scripts/dev.py      Arranque, reinicio y escaneos
docs/               arquitectura.md, modelo-amenazas.md, devsecops.md y esta guía
.github/            CI de seguridad
```
