#!/bin/sh
# Se ejecuta UNA sola vez, cuando el volumen de datos está vacío (ver `python scripts/dev.py reset`).
#
# Roles (mínimo privilegio, ver docs/arquitectura.md):
#   postgres            superusuario; solo para este arranque. La aplicación nunca lo usa.
#   demobank_migrator   dueño del esquema "app"; ejecuta migraciones (DDL). No lo usa la API en tiempo de ejecución.
#   demobank_app        usuario de la API; solo DML sobre las tablas creadas por el migrator. Sin DDL.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v migrator_pw="$(cat /run/secrets/db_migrator_password)" \
  -v app_pw="$(cat /run/secrets/db_app_password)" \
  -v db="$POSTGRES_DB" <<'SQL'
CREATE ROLE demobank_migrator LOGIN PASSWORD :'migrator_pw'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE ROLE demobank_app LOGIN PASSWORD :'app_pw'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT CONNECTION LIMIT 20;

REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db" TO demobank_migrator, demobank_app;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

CREATE SCHEMA app AUTHORIZATION demobank_migrator;
GRANT USAGE ON SCHEMA app TO demobank_app;
ALTER ROLE demobank_migrator SET search_path = app;
ALTER ROLE demobank_app SET search_path = app;

-- Todo lo que cree el migrator queda accesible para la API solo con DML.
-- Tablas append-only (p. ej. bitácora de auditoría) deben revocar UPDATE/DELETE en su migración.
ALTER DEFAULT PRIVILEGES FOR ROLE demobank_migrator IN SCHEMA app
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO demobank_app;
ALTER DEFAULT PRIVILEGES FOR ROLE demobank_migrator IN SCHEMA app
  GRANT USAGE, SELECT ON SEQUENCES TO demobank_app;
SQL
