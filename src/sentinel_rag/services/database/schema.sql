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

CREATE TABLE IF NOT EXISTS access_levels (
    access_level_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    access_level_name VARCHAR(50) UNIQUE NOT NULL -- 'public', 'internal', 'confidential'
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_position (
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    department_id UUID REFERENCES departments(department_id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(role_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, department_id, role_id)
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

-- GIN Index for fast metadata filtering
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_document_chunks_metadata ON document_chunks USING GIN (metadata);
