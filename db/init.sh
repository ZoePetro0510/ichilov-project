#!/bin/bash
# Runs once when the Postgres container starts with an empty data folder.
# 1. Enables pgvector.
# 2. Creates a read-only user for the agent's SQL tool (used on Day 4),
#    so even a bad generated query can never change or delete data.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE ROLE ${AGENT_DB_USER} WITH LOGIN PASSWORD '${AGENT_DB_PASSWORD}';
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${AGENT_DB_USER};
    GRANT USAGE ON SCHEMA public TO ${AGENT_DB_USER};

    -- No table access yet: scripts.init_db grants SELECT on "documents" only,
    -- so the agent can never read chunks, queries or agent_steps.
EOSQL
