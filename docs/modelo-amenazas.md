# Modelo de amenazas (STRIDE)

> Responsable: Arquitectura y DevSecOps · Entregable 1 (semanas 1 y 2) · Última revisión: 2026-10-31
>
> Se apoya en el diagrama, los flujos (`F*`), los límites de confianza (`TB-*`), los activos (`A-*`) y las
> decisiones (`D-*`) de [arquitectura.md](arquitectura.md). Es un documento vivo: se actualiza cuando cambia el
> diseño o aparece un hallazgo nuevo.

## 1. Metodología

1. Se parte del diagrama de flujo de datos (DFD) de la arquitectura.
2. A cada elemento se le aplican las categorías **STRIDE** que le corresponden (sección 3).
3. Cada amenaza recibe un ID estable `T-xx`, un riesgo inherente, una mitigación, un responsable y una forma
   concreta de **verificar** que la mitigación funciona.
4. Las amenazas alimentan el registro de vulnerabilidades y los casos de prueba de seguridad, para cerrar la
   cadena **amenaza → riesgo → mitigación → implementación → prueba → resultado**.

| Letra | Categoría | Propiedad que se viola |
|---|---|---|
| **S** | Spoofing (suplantación) | Autenticación |
| **T** | Tampering (manipulación) | Integridad |
| **R** | Repudiation (repudio) | No repudio |
| **I** | Information disclosure (divulgación) | Confidencialidad |
| **D** | Denial of service (denegación de servicio) | Disponibilidad |
| **E** | Elevation of privilege (elevación de privilegios) | Autorización |

**Escala de riesgo.** Riesgo = Probabilidad × Impacto, cada uno de 1 (bajo) a 3 (alto).

| Riesgo | Valor |
|---|---|
| Alto | 6 a 9 |
| Medio | 3 a 4 |
| Bajo | 1 a 2 |

**Responsables** (por rol del equipo): **Arq** = Arquitectura y DevSecOps · **Back** = Backend y seguridad de acceso ·
**Front** = Frontend y pruebas de seguridad · **Docs** = Documentación, requisitos y gestión.

## 2. Agentes de amenaza

| Agente | Motivación | Capacidad |
|---|---|---|
| Atacante externo anónimo | Robar cuentas o dinero; dañar el servicio | Herramientas automatizadas, listas de contraseñas filtradas |
| Cliente malicioso autenticado | Obtener saldo que no le corresponde; ver datos de otros | Cuenta legítima; manipula peticiones con un proxy (Burp, ZAP) |
| Administrador malicioso o con cuenta robada | Encubrir fraude, alterar registros | Acceso al panel de administración |
| Integrante del equipo (error, no malicia) | — | Puede subir un secreto, agregar una dependencia vulnerable o desactivar un control |
| Proveedor comprometido (cadena de suministro) | Ejecutar código en el sistema | Paquete de PyPI, imagen de Docker o GitHub Action alterada |

## 3. STRIDE por elemento

| Elemento del DFD | Tipo | S | T | R | I | D | E |
|---|---|---|---|---|---|---|---|
| Usuario / navegador | Entidad externa | T-01, T-02 | | T-11 | | | |
| Proxy Nginx | Proceso | T-05 | T-23 | T-12 | T-14 | T-18 | |
| API FastAPI | Proceso | T-03, T-17 | T-07, T-09, T-10 | T-11 | T-13, T-14 | T-19 | T-20, T-21 |
| PostgreSQL | Almacén | | T-06, T-08 | T-11 | T-16 | T-19 | |
| Secretos (`secrets/`, `/run/secrets`) | Almacén | | | | T-15 | | |
| F1 navegador → proxy | Flujo | T-04 | T-04 | | T-04 | | |
| F3 proxy → API | Flujo | T-12 | | | | | |
| F4 API → BD | Flujo | | T-06 | | T-16 | | |
| F7 repositorio y CI | Proceso | | T-22 | | T-15 | | T-22 |
| F8 logs | Almacén | | | T-24 | T-24 | | |

## 4. Amenazas identificadas

Estado: Implementado y verificado · Parcial · Pendiente · Riesgo aceptado (ver sección 6).

### Spoofing (suplantación)

| ID | Elemento | Escenario | P | I | Riesgo | Mitigación | Resp. | Estado | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| **T-01** | API (login), A-01 | Un atacante usa una contraseña débil o filtrada en otro sitio para entrar a la cuenta de un cliente y vaciar su saldo | 3 | 3 | 9 | Política de contraseñas (12 a 128 caracteres y distinta del usuario); hash **Argon2id** con sal. Fuera del alcance: MFA y lista de contraseñas comunes | Back, Arq (hash) | | Prueba unitaria rechaza contraseñas débiles; en la BD los hashes empiezan con `$argon2id$` (verificado en `tests/test_auth.py`) |
| **T-02** | Navegador, API, A-02 | Robo o reutilización de la sesión: cookie leída por XSS, token sin expiración, sesión que sigue viva tras cerrar sesión | 2 | 3 | 6 | Sesión guardada en el servidor (token aleatorio de 256 bits; en la BD solo su hash); cookie `HttpOnly; SameSite=Strict`; expira a los 30 minutos de inactividad; sesión nueva en cada login; se borra en el servidor al cerrar sesión | Back | | Reusar el token tras logout → 401; token alterado → 401; sesión vencida → 401 (verificado en `tests/test_auth.py`); ZAP revisa los atributos de la cookie |
| **T-03** | Proxy, API (login) | Fuerza bruta o *credential stuffing* contra `/api/auth/login` | 3 | 3 | 9 | Rate limiting en el borde: 10 req/min por IP en `/api/auth/` (D-10); bloqueo de 15 minutos por cuenta tras 5 intentos fallidos; mensajes genéricos | Arq (borde), Back (por cuenta) | | 9 peticiones seguidas → `429` desde la 7ª (verificado 2026-10-31); 5 intentos fallidos a una cuenta → bloqueo, incluso con la clave correcta (verificado en `tests/test_auth.py`) |
| **T-04** | F1 (y F3, F4) | Interceptar o modificar el tráfico (WiFi pública, proxy malicioso) para robar credenciales o alterar una transferencia | 1 | 3 | 3 | Puertos publicados solo en `127.0.0.1`: el tráfico entre el navegador y el proxy no sale de la máquina; redes internas sin otros participantes (D-03, D-04) | Arq | | `docker compose ps` y `Get-NetTCPConnection`/`ss`: el puerto 8080 solo escucha en `127.0.0.1` (verificado). Ver RA-01 |
| **T-05** | Proxy | *Host header injection* (enlaces de recuperación de contraseña apuntando a un dominio del atacante, redirecciones abiertas) y *DNS rebinding* | 2 | 2 | 4 | Servidor por defecto que responde `421` a cualquier Host distinto de `localhost`/`127.0.0.1`; `Host` fijo hacia la API (D-11) | Arq | | `Host: evil.example` → `421` (verificado). **Detectado por Semgrep (SAST-001) y corregido** |

### Tampering (manipulación)

| ID | Elemento | Escenario | P | I | Riesgo | Mitigación | Resp. | Estado | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| **T-06** | API → BD (F4) | Inyección SQL en búsquedas, filtros o historial para leer o modificar datos de otros | 2 | 3 | 6 | ORM o consultas parametrizadas, sin concatenar SQL; el rol `demobank_app` no puede hacer DDL (D-07); Semgrep detecta SQL armado con strings | Back, Arq (rol, SAST) | | Semgrep en CI; escaneo activo de ZAP; payloads como `' OR 1=1--` en las pruebas. `CREATE/DROP` como `demobank_app` → rechazado (verificado) |
| **T-07** | API (transferencias, registro, perfil) | Manipular parámetros: monto negativo o cero, más decimales de los permitidos, monto mayor al saldo, cuenta de origen ajena enviada en el cuerpo, o *mass assignment* (`"rol": "admin"`, `"saldo": 1000000` en el registro) | 3 | 3 | 9 | Esquemas Pydantic con `extra="forbid"` y rangos (`gt=0`, máximo por operación); la cuenta de origen sale **siempre** de la sesión, nunca del cuerpo; dinero en centavos (enteros); `CHECK (saldo >= 0)` en la BD | Back | | Casos de prueba con montos `-100`, `0`, `0.001`, `10^12` y campos extra → `422`; la cuenta de origen sale siempre de la sesión: un campo de origen enviado en el cuerpo se rechaza (verificado en `tests/test_transfers.py`) |
| **T-08** | API, BD | **Doble gasto**: dos transferencias simultáneas leen el mismo saldo y ambas se aprueban; o se reenvía (*replay*) la misma petición | 2 | 3 | 6 | Una sola transacción con `SELECT ... FOR UPDATE` sobre ambas cuentas en orden fijo; `CHECK (saldo >= 0)`; llave de idempotencia por transferencia | Back | | Prueba que lanza N transferencias concurrentes y verifica que la suma de saldos se conserva; reenvío con la misma llave → no duplica (verificado en `tests/test_transfers.py`: 10 transferencias simultáneas, solo se aprueban las que alcanza el saldo y el dinero total se conserva) |
| **T-09** | Navegador, API | **CSRF**: un sitio malicioso hace que el navegador del cliente, con sesión abierta, envíe una transferencia | 2 | 3 | 6 | `SameSite=Strict`; token anti-CSRF en la cabecera `X-CSRF-Token` (se entrega al iniciar sesión); mismo origen sin CORS (D-12) | Front, Back | | Backend: un `POST` sin la cabecera `X-CSRF-Token` → `403` (verificado en `tests/test_auth.py`); falta que el frontend la envíe; ZAP revisa los tokens anti-CSRF |
| **T-10** | Frontend, API | **XSS almacenado**: un script en el concepto de una transferencia o en el nombre de usuario se ejecuta en el historial de la víctima o en el panel del administrador | 2 | 3 | 6 | Escapar la salida (el framework lo hace por defecto; prohibido insertar HTML crudo); validar longitud y caracteres; **CSP sin `unsafe-inline`** (D-09); cookies `HttpOnly` | Front, Arq (CSP) | | Payloads `<script>alert(1)</script>` e `<img src=x onerror=alert(1)>` en el concepto → se ven como texto; la consola muestra la violación de CSP; ZAP |
| **T-23** | Navegador | *Clickjacking*: cargar el sitio en un iframe invisible para engañar al cliente y que confirme una transferencia | 1 | 3 | 3 | `frame-ancestors 'none'` en la CSP y `X-Frame-Options: DENY` | Arq | | Cabeceras presentes en todas las respuestas (verificado); página de prueba con iframe → bloqueada |

### Repudiation (repudio)

| ID | Elemento | Escenario | P | I | Riesgo | Mitigación | Resp. | Estado | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| **T-11** | API, BD, A-06 | Un cliente niega haber hecho una transferencia; un administrador o una API comprometida borra o edita registros para encubrir un fraude | 2 | 3 | 6 | Bitácora de eventos de seguridad (login correcto y fallido, transferencias, cambios de rol) con usuario, acción, recurso, IP y fecha del servidor; tabla *append-only* (`REVOKE UPDATE, DELETE` a `demobank_app`) | Back, Arq (privilegios BD) | | `UPDATE`/`DELETE` sobre la bitácora como `demobank_app` → `permission denied` (verificado); cada operación deja su registro (verificado en `tests/test_auth.py`) |
| **T-12** | Proxy → API (F3) | Falsificar la IP de origen con `X-Forwarded-For` para evadir el rate limiting o ensuciar la bitácora | 3 | 2 | 6 | El proxy **sobrescribe** `X-Forwarded-For` con la IP real; Uvicorn solo acepta cabeceras de proxy desde la subred `edge` (D-11) | Arq | | Petición con `X-Forwarded-For: 1.2.3.4` → el backend registra la IP real, no `1.2.3.4` (verificado) |
| **T-24** | Logs (F8) | Registro insuficiente (un ataque pasa desapercibido) o excesivo (contraseñas, tokens o datos personales en los logs) | 2 | 2 | 4 | Definir qué se registra (eventos de seguridad) y qué nunca (contraseñas, tokens, datos completos); secretos como `SecretStr`; `hide_parameters` en SQLAlchemy | Back, Arq | | Revisar los logs después de un login y una transferencia: no aparece la contraseña ni el token. `repr(settings)` no muestra secretos (prueba automatizada) |

### Information disclosure (divulgación de información)

| ID | Elemento | Escenario | P | I | Riesgo | Mitigación | Resp. | Estado | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| **T-13** | API, A-03, A-04 | **IDOR**: un cliente cambia el ID en `/api/cuentas/{id}` o `/api/transacciones/{id}` y ve saldos o movimientos ajenos | 3 | 3 | 9 | Cada consulta filtra por el dueño autenticado, no solo por ID; IDs no secuenciales (UUID) como defensa adicional; responder `404` en vez de `403` para no confirmar que el recurso existe | Back | | Prueba con dos usuarios: A pide un recurso de B → `404` (verificado en `tests/test_transfers.py`) |
| **T-14** | API, Proxy | Trazas de error, mensajes de la BD, versión del servidor o `/api/docs` expuestos en producción | 2 | 2 | 4 | Manejador global de errores con respuesta genérica; `server_tokens off`, `--no-server-header`, `proxy_hide_header`; documentación apagada por defecto (D-08, D-14) | Arq, Back | | Pruebas automatizadas: health con BD caída → `503` sin detalle; `/api/docs` → `404` fuera de desarrollo. manejador global: error interno → `500` genérico y `422` sin devolver los datos enviados (verificado en `tests/test_auth.py`) |
| **T-15** | Repositorio, contenedores, A-07 | Secretos expuestos: `.env` o contraseñas en un commit, secretos en variables de entorno, en imágenes o en logs | 3 | 3 | 9 | `secrets/` y `.env` en `.gitignore`; Gitleaks en pre-commit y en CI sobre todo el historial; Docker secrets en archivo; secretos generados por máquina, distintos en cada clon (D-05) | Arq | | Gitleaks: `no leaks found`; `env \| grep -ci password` en el backend → `0` (verificado) |
| **T-16** | BD, A-01 a A-06 | Acceso directo a la BD o exfiltración masiva por un puerto expuesto, credenciales por defecto o una API comprometida | 2 | 3 | 6 | BD sin puertos publicados y en red interna; el proxy no la alcanza; contraseñas aleatorias de 256 bits; rol de la API sin DDL; la API no tiene salida a internet (D-01, D-03, D-07) | Arq | | Sin puerto en `docker compose ps`; `nc db 5432` desde el proxy falla; salida a internet desde la API falla (verificado) |
| **T-17** | API (login, registro) | Enumeración de usuarios por mensajes distintos ("el usuario no existe" vs. "contraseña incorrecta") o por diferencias en el tiempo de respuesta | 3 | 1 | 3 | Mensajes genéricos; calcular un hash aunque el usuario no exista (tiempo constante); rate limiting | Back | | Comparar respuestas y tiempos para un usuario existente y uno inexistente → indistinguibles (verificado en `tests/test_auth.py`) |

### Denial of service (denegación de servicio)

| ID | Elemento | Escenario | P | I | Riesgo | Mitigación | Resp. | Estado | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| **T-18** | Proxy, API | Ráfagas de peticiones, cuerpos enormes o conexiones lentas (*slowloris*) | 2 | 2 | 4 | Rate limiting; cuerpo máximo de 64 KB; tiempos de espera de 10 s; límites de memoria y procesos por contenedor; reinicio automático (D-06, D-10) | Arq | | `POST` de 70 KB → `413`; ráfaga → `429` (verificado) |
| **T-19** | API → BD | Agotar la BD con consultas sin paginar (historial completo) o abriendo muchas conexiones | 2 | 2 | 4 | Paginación con tamaño máximo; `CONNECTION LIMIT 20` para `demobank_app`; pool de conexiones; `statement_timeout` | Back, Arq (límite de conexiones) | | Pedir `page_size=100000` → se limita al máximo |

### Elevation of privilege (elevación de privilegios)

| ID | Elemento | Escenario | P | I | Riesgo | Mitigación | Resp. | Estado | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| **T-20** | API | Un cliente invoca endpoints de administrador (bloquear cuentas, ver la bitácora) porque la autorización solo se aplica en el frontend | 2 | 3 | 6 | Autorización por rol en **cada** endpoint, denegada por defecto; el rol se lee del servidor, nunca del cuerpo ni de un token sin verificar | Back, Docs (matriz de roles) | | Token de cliente contra cada endpoint de administrador → `403` (verificado en `tests/test_transfers.py`) |
| **T-21** | Contenedores, host | Ejecución remota de código en la API (dependencia vulnerable) usada para escalar a root, leer secretos de otros servicios o moverse a la BD | 1 | 3 | 3 | Sin root; FS solo lectura; `cap_drop: ALL`; `no-new-privileges`; cada servicio monta solo sus secretos; redes segmentadas sin salida (D-03, D-06) | Arq | | `id -u` ≠ 0, `touch /probe` falla y la API no tiene salida a internet (verificado) |
| **T-22** | Repositorio y CI (F7) | Cadena de suministro: dependencia con CVE, paquete malicioso recién publicado (*typosquatting*), GitHub Action comprometida, imagen base vulnerable | 2 | 3 | 6 | Versiones fijadas; pip-audit y npm audit en cada push y cada semana; revisión de dependencias en PRs; actions fijadas por SHA; imágenes oficiales con tag fijo (D-13); revisión manual de versiones antes de la entrega. Pendiente: escaneo de imágenes (Trivy) | Arq | | pip-audit: `No known vulnerabilities found`; npm audit: `found 0 vulnerabilities` (verificado) |

## 5. Casos de abuso

Escenarios de ataque escritos como historias, para convertirlos en casos de prueba de seguridad.

| ID | Como… quiero… para… | Amenazas | Resultado esperado |
|---|---|---|---|
| CA-01 | Como cliente malicioso, quiero transferir **-500** a otro usuario para quitarle dinero | T-07 | `422`; los saldos no cambian |
| CA-02 | Como cliente malicioso, quiero lanzar **20 transferencias simultáneas** con el mismo saldo para gastarlo varias veces | T-08 | Solo se aprueban las que alcanza el saldo; la suma total se conserva |
| CA-03 | Como cliente curioso, quiero **cambiar el ID** en la URL para ver los movimientos de otro | T-13 | `404` |
| CA-04 | Como atacante, quiero poner un **script en el concepto** de una transferencia para robar la sesión del administrador cuando revise la bitácora | T-10, T-02, T-20 | El script se muestra como texto; la CSP bloquea su ejecución |
| CA-05 | Como atacante, quiero probar **10 000 contraseñas** contra una cuenta | T-03, T-01 | `429` y bloqueo de la cuenta |
| CA-06 | Como atacante, quiero enviar un **`X-Forwarded-For` falso** para no quedar registrado | T-12 | Se registra la IP real |
| CA-07 | Como atacante, quiero **registrarme con `"rol": "admin"`** en el cuerpo | T-07, T-20 | `422` o el campo se ignora; la cuenta queda como `cliente` |
| CA-08 | Como sitio malicioso, quiero que el navegador de un cliente con sesión abierta **envíe una transferencia** | T-09 | Rechazada por `SameSite` y token anti-CSRF |
| CA-09 | Como integrante del equipo, **subo el `.env` o una contraseña** por error | T-15 | El hook de pre-commit lo bloquea; si llega al repo, el CI falla |

## 6. Riesgos aceptados

| ID | Riesgo | Por qué se acepta | Qué se haría en producción |
|---|---|---|---|
| RA-01 | Tráfico sin cifrar (F1, F3 y F4) | Todo ocurre dentro de la misma máquina: el proxy solo escucha en `127.0.0.1` y las demás redes son internas, sin otros participantes | Cifrar el tráfico antes de exponer el sistema fuera de un equipo local |
| RA-02 | `/api/docs` con CSP relajada y recursos de un CDN | Solo existe con `APP_ENV=development`; en producción la API responde `404` | Sin cambios: ya está apagado por defecto |
| RA-03 | La cabecera `Server: nginx` sigue presente (sin versión) | Quitarla del todo requiere un módulo extra; la versión ya no se revela | Módulo `headers-more` o un WAF delante |

## 7. Resumen

24 amenazas en total.

| Riesgo inherente | Cantidad | IDs |
|---|---|---|
| Alto | 15 | T-01, T-02, T-03, T-06, T-07, T-08, T-09, T-10, T-11, T-12, T-13, T-15, T-16, T-20, T-22 |
| Medio | 9 | T-04, T-05, T-14, T-17, T-18, T-19, T-21, T-23, T-24 |
| Bajo | 0 | — |

| Estado al 2026-11-09 | Cantidad | IDs |
|---|---|---|
| Implementado y verificado | 17 | T-02, T-03, T-04, T-05, T-07, T-08, T-11, T-12, T-13, T-14, T-15, T-16, T-17, T-18, T-20, T-21, T-23 |
| Parcial | 7 | T-01, T-06, T-09, T-10, T-19, T-22, T-24 |
| Pendiente | 0 | — |

Las parciales esperan al frontend (T-09 y T-10: enviar el token CSRF y escapar la salida), a las pruebas dinámicas con ZAP
(T-06) o a mejoras menores: T-01 sin MFA ni lista de contraseñas comunes, T-19 sin `statement_timeout`, T-22 sin escaneo
de imágenes y T-24 pendiente de revisar los logs completos.

## 8. Trazabilidad

Cada amenaza debe poder seguirse hasta su evidencia:

```
T-xx (este documento)
 └─ riesgo (P × I, sección 4)
     └─ mitigación y decisión D-xx (arquitectura.md)
         └─ implementación (archivo y línea, o PR)
             └─ prueba (caso de prueba, escaneo de ZAP/Semgrep)
                 └─ resultado y, si falló, hallazgo en el registro de vulnerabilidades → corrección → re-prueba
```

Ejemplo completo, ya cerrado:

| Amenaza | Riesgo | Mitigación | Implementación | Prueba | Resultado |
|---|---|---|---|---|---|
| T-05 Host header injection | 4 | D-11: rechazar Host ajenos; `Host` fijo hacia la API | `proxy/default.conf` (servidor por defecto `421`), `proxy/snippets/proxy-backend.conf` | Semgrep `request-host-used` (SAST-001) y `curl -H "Host: evil.example"` | Hallazgo en el primer escaneo → corregido → re-escaneo con 0 hallazgos; `curl` devuelve `421` |
