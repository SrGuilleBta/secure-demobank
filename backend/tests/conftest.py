import os

# Valores de prueba (no son secretos reales). Deben existir antes de importar app.main.
os.environ.setdefault("DB_APP_PASSWORD", "test-only")
os.environ.setdefault("APP_SECRET_KEY", "test-only")
