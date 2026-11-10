-- Esquema de Secure DemoBank. SQL puro: lo carga db/init/02-schema.sh (con el rol demobank_migrator)
-- y el CI lo aplica directamente a una base de pruebas. Solo se ejecuta al crear la base de datos
-- (para rehacerla: `python scripts/dev.py reset` y luego `up`).

-- Usuarios. El nombre va en minúsculas y con un alfabeto cerrado; la contraseña solo se guarda como hash Argon2id.
CREATE TABLE users (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    username        text        NOT NULL UNIQUE CHECK (username ~ '^[a-z0-9_]{3,32}$'),
    password_hash   text        NOT NULL,
    role            text        NOT NULL DEFAULT 'cliente' CHECK (role IN ('cliente', 'administrador')),
    failed_attempts integer     NOT NULL DEFAULT 0,
    locked_until    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- Saldo en centavos (entero, nunca decimales). La BD impide saldos negativos aunque la aplicación falle.
CREATE TABLE accounts (
    user_id       uuid   PRIMARY KEY REFERENCES users (id),
    balance_cents bigint NOT NULL CHECK (balance_cents >= 0)
);

-- Sesiones del lado del servidor. Solo se guarda el hash del token: si la tabla se filtra, las cookies no sirven.
CREATE TABLE sessions (
    token_hash text        PRIMARY KEY,
    user_id    uuid        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    csrf_token text        NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE transfers (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user_id    uuid        NOT NULL REFERENCES users (id),
    to_user_id      uuid        NOT NULL REFERENCES users (id),
    amount_cents    bigint      NOT NULL CHECK (amount_cents > 0),
    concept         text        NOT NULL DEFAULT '' CHECK (char_length(concept) <= 100),
    idempotency_key uuid        NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    CHECK (from_user_id <> to_user_id),
    -- Reenviar la misma petición no duplica la transferencia (amenaza T-08).
    UNIQUE (from_user_id, idempotency_key)
);
CREATE INDEX transfers_from_idx ON transfers (from_user_id, created_at DESC);
CREATE INDEX transfers_to_idx   ON transfers (to_user_id, created_at DESC);

-- Transferencias con los nombres de usuario ya unidos: la API la consulta con SQL fijo (sin armar texto).
CREATE VIEW transfer_details AS
SELECT t.id, t.from_user_id, t.to_user_id, fu.username AS from_username, tu.username AS to_username,
       t.amount_cents, t.concept, t.created_at
FROM transfers t
JOIN users fu ON fu.id = t.from_user_id
JOIN users tu ON tu.id = t.to_user_id;

-- Bitácora de auditoría. Sin llave foránea a propósito: el registro sobrevive aunque se borre el usuario.
-- db/init/02-schema.sh le revoca UPDATE y DELETE al rol de la API (solo se puede insertar y leer).
CREATE TABLE audit_log (
    id         bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    user_id    uuid,
    action     text        NOT NULL,
    detail     text,
    ip         text
);
CREATE INDEX audit_log_created_idx ON audit_log (created_at DESC);
