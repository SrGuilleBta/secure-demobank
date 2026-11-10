# Frontend

React + Vite. El código vive aquí; el proxy lo compila dentro de su imagen y lo sirve (ver `proxy/Dockerfile`).

## Trabajar en el frontend

Con el stack levantado (`python scripts/dev.py up` desde la raíz del repo):

```bash
cd frontend
```

```bash
npm install
```

```bash
npm run dev
```

Abre <http://localhost:5173>. Los cambios se ven al instante y las peticiones a `/api` se mandan al proxy
(`vite.config.js`), así que funciona igual que en el stack real.

Para ver el resultado final dentro del stack (build de producción servido por Nginx), desde la raíz del repo:

```bash
python scripts/dev.py up
```

Reconstruye la imagen del proxy con tu código y deja la aplicación en <http://localhost:8080>.

## Reglas que ya resuelve la arquitectura

- El navegador solo habla con el proxy. El frontend y la API comparten origen, así que **no hace falta CORS** y las
  cookies pueden ser `SameSite=Strict`.
- La API vive bajo `/api/`. Las rutas del frontend (por ejemplo `/login`) las resuelve React: el proxy devuelve
  `index.html` para cualquier ruta que no sea un archivo ni `/api/`.
- La CSP del sitio está en `proxy/default.conf` (`location /`) y **no permite scripts ni estilos inline**: todo JS y CSS
  debe ir en archivos propios (Vite ya lo hace así). Si una librería lo requiere, se documenta y se ajusta la CSP.
- Nunca usar `dangerouslySetInnerHTML` ni insertar HTML crudo (T-10). No guardar tokens en `localStorage`.

## Dependencias

Las versiones están fijadas en `package.json` (sin `^`) y `package-lock.json` se sube al repo. Para agregar una librería:

```bash
npm install --save-exact nombre-de-la-libreria
```

El CI corre `npm audit` y falla si hay vulnerabilidades moderadas o peores. Puedes revisarlo antes de subir con
`python scripts/dev.py scan`.
