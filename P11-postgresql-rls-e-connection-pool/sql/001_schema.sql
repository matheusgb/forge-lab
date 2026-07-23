DROP TABLE IF EXISTS documents CASCADE;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tenant_app') THEN
        CREATE ROLE tenant_app LOGIN PASSWORD 'tenant_app';
    END IF;
END
$$;

ALTER ROLE tenant_app WITH
    LOGIN
    PASSWORD 'tenant_app'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

CREATE TABLE documents (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id uuid NOT NULL,
    title text NOT NULL CHECK (length(btrim(title)) > 0)
);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_owns_document ON documents
    FOR ALL
    TO tenant_app
    USING (
        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
    )
    WITH CHECK (
        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
    );

GRANT USAGE ON SCHEMA public TO tenant_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON documents TO tenant_app;
GRANT USAGE, SELECT ON SEQUENCE documents_id_seq TO tenant_app;
