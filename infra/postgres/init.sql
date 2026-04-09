-- Bootstrap script: extensions only.
-- All table DDL is managed by Alembic migrations (run `make migrate`).
-- Adding tables here causes conflicts with Alembic; don't do it.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
