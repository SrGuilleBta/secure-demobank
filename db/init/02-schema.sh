#!/bin/sh
# Se ejecuta UNA sola vez, después de 01-roles.sh, cuando el volumen de datos está vacío.
# Crea las tablas como demobank_migrator (así quedan a su nombre y la API recibe solo DML por los
# privilegios por defecto definidos en 01-roles.sh) y deja la bitácora de auditoría como solo-inserción.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
SET ROLE demobank_migrator;
SET search_path = app;
\i /schema.sql
RESET ROLE;

REVOKE UPDATE, DELETE, TRUNCATE ON app.audit_log FROM demobank_app;
SQL
