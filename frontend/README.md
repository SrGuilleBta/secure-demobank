# Frontend

**Libre elección de quien desarrolle esta parte** (preferentemente React).

Mientras tanto, el proxy sirve `frontend/public/` como sitio estático para que el stack completo arranque.

Lo que la arquitectura ya resuelve, sea cual sea la opción elegida:

- El navegador solo habla con el proxy (`http://localhost:8080`). El frontend y la API comparten origen,
  así que **no hace falta CORS** y las cookies pueden ser `SameSite=Strict`.
- La API vive bajo `/api/`; todo lo demás lo sirve el proxy desde `frontend/public/` (o el build de la SPA).
- La CSP del sitio está en `proxy/default.conf` (`location /`) y no permite scripts ni estilos inline:
  todo JS/CSS debe ir en archivos propios. Si una librería lo requiere, se documenta y se ajusta la CSP.

Si se elige una SPA, el build (`dist/`) se monta en el proxy en lugar de `public/` (cambio en `docker-compose.yml`).
