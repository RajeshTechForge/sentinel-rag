-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
--
-- NOTE: No foreign key constraints to main database tables.
-- Audit logs are denormalized and immutable for compliance.
-- Even if entities are deleted from main DB, audit trail remains intact.
-- ============================================

-- Main audit log table
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Actor information (denormalized - no FK to users table)
    user_id UUID,                         -- Reference only, no FK constraint
    user_email VARCHAR(255),              -- Denormalized for data retention
    session_id VARCHAR(255),  -- For tracking user sessions
    ip_address INET,
    user_agent TEXT,
    
    -- Event classification
    event_category VARCHAR(50) NOT NULL,  -- authentication, authorization, data_access, modification, admin, system
    event_type VARCHAR(100) NOT NULL,     -- login, document_query, permission_denied, etc.
    action VARCHAR(100) NOT NULL,         -- READ, WRITE, DELETE, UPDATE, EXECUTE
    outcome VARCHAR(20) NOT NULL,         -- success, failure, partial
    
    -- Resource information
    resource_type VARCHAR(50),            -- document, chunk, user, role, department
    resource_id UUID,
    resource_name VARCHAR(255),           -- Denormalized for readability
    
    -- Access control context (denormalized - no FK constraints)
    department_id UUID,                   -- Reference only, no FK constraint
    department_name VARCHAR(50),          -- Denormalized
    role_id UUID,                         -- Reference only, no FK constraint
    role_name VARCHAR(50),                -- Denormalized
    classification_level VARCHAR(50),     -- public, internal, confidential
    
    -- Compliance-specific fields
    pii_accessed BOOLEAN DEFAULT FALSE,
    pii_types JSONB,                      -- ["email", "ssn", "phone"] if PII was accessed
    data_redacted BOOLEAN DEFAULT FALSE,
    
    -- Change tracking (for modifications)
    changes JSONB,                        -- {"before": {...}, "after": {...}}
    
    -- Additional context
    query_text TEXT,                      -- For RAG queries (sanitized)
    error_message TEXT,                   -- If outcome = failure
    metadata JSONB,                       -- Flexible field for additional data
    
    -- Retention management
    retention_years INTEGER DEFAULT 7,    -- Based on regulation
    archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP
);

-- Query performance audit (for RAG-specific monitoring)
CREATE TABLE IF NOT EXISTS query_audit (
    query_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_id UUID REFERENCES audit_logs(log_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    user_id UUID,                         -- Reference only, no FK constraint
    query_text_hash VARCHAR(64),          -- SHA-256 hash of query (privacy)
    
    -- RAG-specific metrics
    chunks_retrieved INTEGER,
    chunks_accessed UUID[],               -- Array of chunk IDs
    documents_accessed UUID[],            -- Array of document IDs
    vector_search_time_ms DECIMAL(10,2),
    llm_processing_time_ms DECIMAL(10,2),
    total_response_time_ms DECIMAL(10,2),
    
    -- Access control applied
    filters_applied JSONB,                -- {"department": "finance", "role": "manager"}
    chunks_filtered INTEGER,              -- How many chunks were filtered out by RBAC
    
    metadata JSONB
);

-- Authentication events (detailed tracking)
CREATE TABLE IF NOT EXISTS auth_audit (
    auth_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_id UUID REFERENCES audit_logs(log_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    user_id UUID,                         -- Reference only, no FK constraint
    email VARCHAR(255) NOT NULL,
    
    auth_method VARCHAR(50),              -- email_password, oauth, sso, api_key
    event_type VARCHAR(50) NOT NULL,      -- login_success, login_failure, logout, token_refresh, password_change
    
    ip_address INET,
    user_agent TEXT,
    geolocation JSONB,                    -- {"country": "US", "city": "NYC"} if available
    
    -- Security tracking
    failed_attempts_count INTEGER DEFAULT 0,
    account_locked BOOLEAN DEFAULT FALSE,
    mfa_used BOOLEAN DEFAULT FALSE,
    
    metadata JSONB
);

-- Data modification audit (for GDPR Article 30 compliance)
CREATE TABLE IF NOT EXISTS modification_audit (
    modification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_id UUID REFERENCES audit_logs(log_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    user_id UUID,                         -- Reference only, no FK constraint
    
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    operation VARCHAR(20) NOT NULL,       -- INSERT, UPDATE, DELETE
    
    -- Change details
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    
    -- Justification (if required by policy)
    reason TEXT,
    approved_by UUID,                     -- Reference only, no FK constraint
    
    metadata JSONB
);

-- INDEXES FOR PERFORMANCE
-- -----------------------

-- Time-based queries (most common for compliance reports)
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp_category ON audit_logs(timestamp DESC, event_category);

-- User activity tracking
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_email ON audit_logs(user_email, timestamp DESC);

-- Resource access tracking
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id, timestamp DESC);

-- Compliance queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_pii ON audit_logs(pii_accessed, timestamp DESC) WHERE pii_accessed = TRUE;
CREATE INDEX IF NOT EXISTS idx_audit_logs_outcome ON audit_logs(outcome, timestamp DESC) WHERE outcome = 'failure';

-- Retention management
CREATE INDEX IF NOT EXISTS idx_audit_logs_retention ON audit_logs(archived, timestamp) WHERE archived = FALSE;

-- Query audit indexes
CREATE INDEX IF NOT EXISTS idx_query_audit_user_timestamp ON query_audit(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_query_audit_timestamp ON query_audit(timestamp DESC);

-- Auth audit indexes
CREATE INDEX IF NOT EXISTS idx_auth_audit_email_timestamp ON auth_audit(email, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_auth_audit_failed ON auth_audit(event_type, timestamp DESC) WHERE event_type = 'login_failure';

-- GIN index for JSONB metadata searches
CREATE INDEX IF NOT EXISTS idx_audit_logs_metadata ON audit_logs USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_audit_logs_pii_types ON audit_logs USING GIN (pii_types);
