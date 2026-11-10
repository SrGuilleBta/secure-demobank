# Imagen del proxy: compila el frontend React y lo sirve con Nginx.
# Se construye desde la raíz del repo (docker-compose.yml: build.context ".").

FROM node:24-alpine AS frontend-build
WORKDIR /app
# Primero solo los manifiestos: la capa de dependencias se reutiliza mientras no cambien.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.30-alpine
# Solo el resultado del build llega a la imagen final: sin Node, sin node_modules, sin código fuente.
COPY --from=frontend-build /app/dist /usr/share/nginx/html
