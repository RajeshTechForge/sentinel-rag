CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================================
--             User and RBAC Management
-- ========================================================

CREATE TABLE IF NOT EXISTS departments (
    department_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    department_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
    role_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_name VARCHAR(50) NOT NULL,
    department_id UUID REFERENCES departments(department_id) ON DELETE CASCADE,
    UNIQUE(role_name, department_id)
);

CREATE TABLE IF NOT EXISTS permission_levels (
    permission_level_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    permission_level_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS access_levels (
    access_level_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    access_level_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS role_access (
    role_id UUID REFERENCES roles(role_id),
    access_level_id UUID REFERENCES access_levels(access_level_id),
    PRIMARY KEY (role_id, access_level_id)
);

CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(100),
    permission_level_id UUID REFERENCES permission_levels(permission_level_id),
    department_id UUID REFERENCES departments(department_id) ON DELETE SET NULL,
    role_id UUID REFERENCES roles(role_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ======================================================
--           M2M Client Credentials (OAuth2)
-- ======================================================

-- Store M2M client credentials for programmatic access
CREATE TABLE IF NOT EXISTS m2m_clients (
    client_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_name VARCHAR(255) NOT NULL,
    client_secret_hash VARCHAR(255) NOT NULL,  -- bcrypt hash of secret
    description TEXT,
    owner_user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    -- Inherit permissions from owner or service account
    service_account_user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    scopes TEXT[],  -- Array of allowed scopes/permissions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,  -- Optional expiration
    metadata JSONB,
    CONSTRAINT unique_client_name_per_owner UNIQUE(client_name, owner_user_id)
);

-- ======================================================
--               Document Management
-- ======================================================

-- Documents metadata
CREATE TABLE IF NOT EXISTS documents (
    doc_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    description TEXT,
    uploaded_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    department_id UUID REFERENCES departments(department_id) ON DELETE SET NULL,
    classification VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Document Chunks (RAG data - vectors stored in Qdrant)
CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id UUID PRIMARY KEY,
    doc_id UUID REFERENCES documents(doc_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER,
    chunk_type VARCHAR(20) DEFAULT 'child',
    parent_chunk_id UUID REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
    searchable_text_tsvector tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    metadata JSONB
);

-- INDEXES FOR PERFORMANCE
-- -----------------------

CREATE INDEX IF NOT EXISTS idx_chunks_fts ON document_chunks USING gin(searchable_text_tsvector);

CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_id ON document_chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_parent_id ON document_chunks(parent_chunk_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_type ON document_chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_roles_department_id ON roles(department_id);
CREATE INDEX IF NOT EXISTS idx_users_department_id ON users(department_id);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_m2m_clients_owner ON m2m_clients(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_m2m_clients_service_account ON m2m_clients(service_account_user_id);
CREATE INDEX IF NOT EXISTS idx_m2m_clients_active ON m2m_clients(is_active) WHERE is_active = TRUE;

-- GIN Index for fast metadata filtering
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata ON document_chunks USING GIN (metadata);
