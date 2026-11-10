#!/usr/bin/env python3
"""Arranque y utilidades del entorno local de Secure DemoBank (Windows, macOS y Linux).

    python scripts/dev.py setup   Genera secretos y .env (no sobrescribe nada existente)
    python scripts/dev.py up      setup + levanta el stack y espera a que responda
    python scripts/dev.py down    Detiene el stack (conserva los datos)
    python scripts/dev.py reset   Detiene el stack y BORRA la base de datos (pide confirmación)
    python scripts/dev.py logs    Sigue los logs de todos los servicios
    python scripts/dev.py test    Pruebas del backend contra un PostgreSQL temporal (requiere pytest instalado)
    python scripts/dev.py admin <usuario>   Convierte a un usuario ya registrado en administrador
    python scripts/dev.py scan    Escaneos locales: Gitleaks, Semgrep, pip-audit y npm audit (los mismos que corre el CI)

Solo usa la biblioteca estándar de Python; requiere Docker.
"""

import argparse
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS_DIR = ROOT / "secrets"
REPORTS_DIR = ROOT / "reports"

# Mismas versiones que .github/workflows/security.yml
GITLEAKS_IMAGE = "zricethezav/gitleaks:v8.30.1"
SEMGREP_IMAGE = "semgrep/semgrep:1.180.0"
PYTHON_IMAGE = "python:3.12-slim-trixie"
NODE_IMAGE = "node:24-alpine"
POSTGRES_IMAGE = "postgres:17-alpine"
TEST_DB_CONTAINER = "demobank-test-db"
TEST_DB_PORT = "55432"
PIP_AUDIT_VERSION = "2.10.1"
SEMGREP_CONFIGS = [
    "p/python", "p/javascript", "p/react", "p/owasp-top-ten", "p/dockerfile", "p/docker-compose", "p/nginx",
]

PASSWORD_SECRETS = ["db_admin_password", "db_migrator_password", "db_app_password"]
KEY_SECRETS = ["app_secret_key"]


def run(cmd: list[str], check: bool = True) -> int:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=check).returncode


def write_secret(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")
    # El directorio es 0700 y bloquea a otros usuarios del host; el archivo queda 0644 para que el
    # usuario sin privilegios de cada contenedor pueda leerlo cuando Docker lo monta en /run/secrets.
    if os.name != "nt":
        path.chmod(0o644)


def cmd_setup(_args: argparse.Namespace) -> None:
    SECRETS_DIR.mkdir(exist_ok=True)
    if os.name != "nt":
        SECRETS_DIR.chmod(0o700)

    for name in PASSWORD_SECRETS + KEY_SECRETS:
        path = SECRETS_DIR / name
        if path.exists():
            continue
        # CSPRNG del sistema operativo; 32 bytes = 256 bits de entropía.
        write_secret(path, secrets.token_urlsafe(32))
        print(f"  secreto generado -> secrets/{name}")

    env_file = ROOT / ".env"
    if not env_file.exists():
        shutil.copyfile(ROOT / ".env.example", env_file)
        print("  .env creado a partir de .env.example")
    print("Setup listo.")


def wait_until_healthy(url: str, timeout_s: int = 90) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(2)
    return False


def cmd_up(args: argparse.Namespace) -> None:
    cmd_setup(args)
    run(["docker", "compose", "up", "-d", "--build"])
    port = read_env().get("HTTP_PORT", "8080")
    url = f"http://localhost:{port}"
    if wait_until_healthy(f"{url}/api/health"):
        print(f"\nSecure DemoBank arriba en {url}")
    else:
        print("\nEl stack no respondió a tiempo. Revisa: python scripts/dev.py logs", file=sys.stderr)
        sys.exit(1)


def cmd_down(_args: argparse.Namespace) -> None:
    run(["docker", "compose", "down"])


def cmd_reset(args: argparse.Namespace) -> None:
    if not args.yes:
        answer = input("Esto BORRA la base de datos local. Escribe 'borrar' para continuar: ")
        if answer.strip() != "borrar":
            print("Cancelado.")
            return
    run(["docker", "compose", "down", "--volumes"])


def cmd_logs(_args: argparse.Namespace) -> None:
    run(["docker", "compose", "logs", "-f", "--tail", "100"], check=False)


def cmd_admin(args: argparse.Namespace) -> None:
    username = args.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,32}", username):
        sys.exit("Nombre de usuario inválido (3 a 32 caracteres: letras, números y guion bajo).")
    # El nombre viaja como variable de psql (:'u'), no pegado al SQL.
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "postgres", "-d", "demobank",
         "-v", "ON_ERROR_STOP=1", "-v", f"u={username}", "-At"],
        cwd=ROOT, input="UPDATE app.users SET role = 'administrador' WHERE username = :'u';",
        text=True, capture_output=True,
    )
    if result.returncode != 0:
        sys.exit(result.stderr.strip() or "No se pudo conectar a la base de datos. ¿Está levantado el stack?")
    if "UPDATE 1" not in result.stdout:
        sys.exit(f"No existe el usuario '{username}'. Regístralo primero desde la aplicación.")
    print(f"{username} ahora es administrador.")


def cmd_test(_args: argparse.Namespace) -> None:
    """Corre pytest contra un PostgreSQL desechable que se crea y se borra solo."""
    run(["docker", "rm", "-f", TEST_DB_CONTAINER], check=False)
    run(["docker", "run", "-d", "--rm", "--name", TEST_DB_CONTAINER, "-e", "POSTGRES_PASSWORD=test",
         "-p", f"127.0.0.1:{TEST_DB_PORT}:5432", POSTGRES_IMAGE])
    try:
        # -h 127.0.0.1 (TCP): durante el arranque inicial la imagen solo escucha por socket local.
        for _ in range(30):
            ready = subprocess.run(
                ["docker", "exec", TEST_DB_CONTAINER, "pg_isready", "-h", "127.0.0.1", "-U", "postgres"],
                capture_output=True,
            )
            if ready.returncode == 0:
                break
            time.sleep(2)
        else:
            sys.exit("La base de datos de pruebas no arrancó.")
        # Se envía como bytes UTF-8: en Windows el texto saldría con la codificación local y PostgreSQL lo rechazaría.
        schema = (ROOT / "db" / "schema.sql").read_bytes()
        subprocess.run(
            ["docker", "exec", "-i", TEST_DB_CONTAINER, "psql", "-U", "postgres", "-q", "-v", "ON_ERROR_STOP=1"],
            input=schema, check=True,
        )
        env = {**os.environ,
               "TEST_DATABASE_URL": f"postgresql+psycopg://postgres:test@127.0.0.1:{TEST_DB_PORT}/postgres"}
        code = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT / "backend", env=env).returncode
    finally:
        run(["docker", "rm", "-f", TEST_DB_CONTAINER], check=False)
    sys.exit(code)


def cmd_scan(_args: argparse.Namespace) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    failures = []
    # En Linux/macOS los reportes se escriben con el usuario del host, no como root.
    as_host_user = ["--user", f"{os.getuid()}:{os.getgid()}"] if os.name != "nt" else []

    # Gitleaks sobre todo el historial de git. GIT_CONFIG_* evita el error de "dubious ownership"
    # porque el repo montado pertenece a otro usuario dentro del contenedor.
    if run([
        "docker", "run", "--rm", "-v", f"{ROOT}:/repo", *as_host_user,
        "-e", "GIT_CONFIG_COUNT=1", "-e", "GIT_CONFIG_KEY_0=safe.directory", "-e", "GIT_CONFIG_VALUE_0=*",
        GITLEAKS_IMAGE, "git", "/repo", "--redact", "--no-banner",
        "--report-format", "sarif", "--report-path", "/repo/reports/gitleaks.sarif",
    ], check=False):
        failures.append("gitleaks")

    semgrep_cmd = ["semgrep", "scan", "--metrics=off", "--error", "--sarif-output=/src/reports/semgrep.sarif"]
    for config in SEMGREP_CONFIGS:
        semgrep_cmd += ["--config", config]
    if run([
        "docker", "run", "--rm", "-v", f"{ROOT}:/src", "-w", "/src", *as_host_user, "-e", "HOME=/tmp",
        SEMGREP_IMAGE, *semgrep_cmd,
    ], check=False):
        failures.append("semgrep")

    if run([
        "docker", "run", "--rm", "-v", f"{ROOT / 'backend'}:/app:ro", PYTHON_IMAGE, "sh", "-c",
        f"pip install --quiet --disable-pip-version-check pip-audit=={PIP_AUDIT_VERSION} "
        "&& pip-audit --strict -r /app/requirements.txt",
    ], check=False):
        failures.append("pip-audit")

    if run([
        "docker", "run", "--rm", "-v", f"{ROOT / 'frontend'}:/app:ro", "-w", "/app", "-e", "HOME=/tmp",
        NODE_IMAGE, "npm", "audit", "--audit-level=moderate",
    ], check=False):
        failures.append("npm-audit")

    print("\nReportes SARIF en reports/")
    if failures:
        print("Con hallazgos: " + ", ".join(failures), file=sys.stderr)
        sys.exit(1)
    print("Sin hallazgos.")


def read_env() -> dict[str, str]:
    env_file = ROOT / ".env"
    values = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup").set_defaults(func=cmd_setup)
    sub.add_parser("up").set_defaults(func=cmd_up)
    sub.add_parser("down").set_defaults(func=cmd_down)
    reset = sub.add_parser("reset")
    reset.add_argument("--yes", action="store_true", help="no pedir confirmación")
    reset.set_defaults(func=cmd_reset)
    sub.add_parser("logs").set_defaults(func=cmd_logs)
    sub.add_parser("test").set_defaults(func=cmd_test)
    admin = sub.add_parser("admin")
    admin.add_argument("username")
    admin.set_defaults(func=cmd_admin)
    sub.add_parser("scan").set_defaults(func=cmd_scan)
    args = parser.parse_args()
    try:
        args.func(args)
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
