# Database Separation Guide

## Overview

Sentinel RAG supports **flexible database architecture** for separating audit logging from core application data. This enables:

- **Compliance**: Isolate audit logs in a separate database for regulatory requirements
- **Performance**: Prevent audit logging from impacting application database performance
- **Security**: Apply different access controls to audit data
- **Scalability**: Scale audit and application databases independently
- **Cost Optimization**: Use different storage tiers for operational vs. audit data

## Architecture

### Database Schemas

The system uses two separate database schemas:

1. **Application Schema** ([database/schema.sql](../src/sentinel_rag/services/database/schema.sql))
   - Users, Departments, Roles
   - Documents metadata
   - Document chunks (content + full-text search indexes)
   - Access control mappings

2. **Audit Schema** ([audit/audit_schema.sql](../src/sentinel_rag/services/audit/audit_schema.sql))
   - Audit logs (main audit trail)
   - Query audit (RAG-specific performance metrics)
   - Auth audit (authentication events)
   - Modification audit (data change tracking)

### Database Managers

- **DatabaseManager** (`services/database/database.py`)
  - Manages application database connections (synchronous, psycopg2)
  - Handles user, role, department, and document operations
  - Performs full-text search for hybrid retrieval

- **AuditDatabaseManager** (`services/audit/audit_database.py`)
  - Manages audit database connections (asynchronous, asyncpg)
  - Handles schema initialization for audit tables
  - Provides connection pool for audit service

## Configuration

### Option 1: Same Database (Default)

Use a single database for both application and audit data.

**.env**
```bash
# Main database
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
POSTGRES_DB="sentinel_db"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="your_password"

# Audit uses same database
AUDIT_USE_SEPARATE_DB="false"
```

This configuration creates all tables (application + audit) in the same database: `sentinel_db`.

### Option 2: Separate Databases

Use dedicated databases for application and audit data.

**.env**
```bash
# Main application database
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
POSTGRES_DB="sentinel_app"
POSTGRES_USER="app_user"
POSTGRES_PASSWORD="app_password"

# Separate audit database
AUDIT_USE_SEPARATE_DB="true"
AUDIT_POSTGRES_HOST="localhost"
AUDIT_POSTGRES_PORT="5432"
AUDIT_POSTGRES_DB="sentinel_audit"
AUDIT_POSTGRES_USER="audit_user"
AUDIT_POSTGRES_PASSWORD="audit_password"
```

This configuration creates:
- **sentinel_app**: Application tables (users, documents, chunks, etc.)
- **sentinel_audit**: Audit tables (audit_logs, query_audit, auth_audit, etc.)

### Option 3: Different Database Servers

Use completely separate PostgreSQL servers.

**.env**
```bash
# Main application database (Production server)
POSTGRES_HOST="app-db.company.com"
POSTGRES_PORT="5432"
POSTGRES_DB="sentinel_app"
POSTGRES_USER="app_user"
POSTGRES_PASSWORD="app_password"

# Separate audit database (Compliance server)
AUDIT_USE_SEPARATE_DB="true"
AUDIT_POSTGRES_HOST="audit-db.company.com"
AUDIT_POSTGRES_PORT="5432"
AUDIT_POSTGRES_DB="sentinel_audit"
AUDIT_POSTGRES_USER="audit_user"
AUDIT_POSTGRES_PASSWORD="audit_password"
```

## Connection Pool Configuration

Both databases support independent connection pool tuning:

**.env**
```bash
# Application database pool
POSTGRES_MIN_POOL_SIZE="5"
POSTGRES_MAX_POOL_SIZE="20"

# Audit database pool (typically smaller)
AUDIT_POSTGRES_MIN_POOL_SIZE="2"
AUDIT_POSTGRES_MAX_POOL_SIZE="10"
```

## Initialization Flow

### Application Startup

When the FastAPI application starts (`app_lifespan` in [dependencies.py](../src/sentinel_rag/api/dependencies.py)):

1. **Initialize Application Database**
   - DatabaseManager connects to main database
   - Executes `database/schema.sql` to create application tables
   - Creates connection pool (synchronous, psycopg2)

2. **Initialize Audit Database** (if `ENABLE_AUDIT_LOGGING=true` in config.json)
   - Determines effective DSN (separate or shared database)
   - AuditDatabaseManager connects to audit database
   - Executes `audit/audit_schema.sql` to create audit tables
   - Creates async connection pool (asyncpg)
   - Initializes AuditService with the pool

3. **Initialize Other Services**
   - QdrantStore (vector database)
   - SentinelEngine (RAG orchestration)

## Usage Examples

### Docker Compose: Same Database

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: sentinel_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_DB: sentinel_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      AUDIT_USE_SEPARATE_DB: "false"
    depends_on:
      - postgres
```

### Docker Compose: Separate Databases

```yaml
services:
  app_db:
    image: postgres:15
    environment:
      POSTGRES_DB: sentinel_app
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: app_pass
    volumes:
      - app_data:/var/lib/postgresql/data

  audit_db:
    image: postgres:15
    environment:
      POSTGRES_DB: sentinel_audit
      POSTGRES_USER: audit_user
      POSTGRES_PASSWORD: audit_pass
    volumes:
      - audit_data:/var/lib/postgresql/data

  api:
    build: .
    environment:
      # Application DB
      POSTGRES_HOST: app_db
      POSTGRES_DB: sentinel_app
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: app_pass
      
      # Audit DB (separate)
      AUDIT_USE_SEPARATE_DB: "true"
      AUDIT_POSTGRES_HOST: audit_db
      AUDIT_POSTGRES_DB: sentinel_audit
      AUDIT_POSTGRES_USER: audit_user
      AUDIT_POSTGRES_PASSWORD: audit_pass
    depends_on:
      - app_db
      - audit_db

volumes:
  app_data:
  audit_data:
```

## Migration Guide

### Migrating from Single to Separate Databases

If you're currently using a single database and want to separate audit data:

1. **Backup Your Current Database**
   ```bash
   pg_dump -h localhost -U postgres sentinel_db > backup.sql
   ```

2. **Create New Audit Database**
   ```bash
   createdb -h localhost -U postgres sentinel_audit
   ```

3. **Export Audit Tables**
   ```bash
   pg_dump -h localhost -U postgres -t audit_logs -t query_audit \
           -t auth_audit -t modification_audit sentinel_db > audit_data.sql
   ```

4. **Update Configuration**
   ```bash
   AUDIT_USE_SEPARATE_DB="true"
   AUDIT_POSTGRES_DB="sentinel_audit"
   # ... other audit DB credentials
   ```

5. **Restart Application** (creates audit schema in new database)

6. **Import Audit Data**
   ```bash
   psql -h localhost -U postgres sentinel_audit < audit_data.sql
   ```

7. **Drop Audit Tables from Main Database** (optional)
   ```sql
   DROP TABLE modification_audit CASCADE;
   DROP TABLE auth_audit CASCADE;
   DROP TABLE query_audit CASCADE;
   DROP TABLE audit_logs CASCADE;
   ```

## Best Practices

### Security

- **Different Credentials**: Use separate database users with minimal permissions
  - Application user: Read/write on application tables only
  - Audit user: Append-only (INSERT) on audit tables

- **Network Isolation**: Place audit database on a separate network segment

- **Access Control**: Restrict direct access to audit database to compliance team

### Performance

- **Connection Pooling**: Audit database typically needs smaller pool (2-10 connections)

- **Indexes**: Audit tables have timestamp-based indexes for query performance

- **Partitioning**: For high-volume systems, consider table partitioning on `timestamp`

### Compliance

- **Retention Policies**: Implement automated archival based on `retention_years`

- **Immutability**: Configure audit database user with INSERT-only permissions

- **Backup & Recovery**: Implement separate backup schedules for audit data

- **Monitoring**: Set up alerts for audit database connectivity issues

## Troubleshooting

### Application starts but audit logging fails

**Symptom**: API starts but no audit logs are written

**Check**:
1. Is `ENABLE_AUDIT_LOGGING=true` in `config/config.json`?
2. Are audit database credentials correct?
3. Check logs for audit database connection errors

### Connection pool exhaustion

**Symptom**: "Too many connections" error

**Solution**:
- Increase `AUDIT_POSTGRES_MAX_POOL_SIZE`
- Check for connection leaks in custom audit code
- Ensure `AuditDatabaseManager.close()` is called on shutdown

### Schema initialization errors

**Symptom**: "Table already exists" or "Permission denied"

**Solution**:
- Drop existing audit tables and restart application
- Grant CREATE permissions to audit database user
- Check PostgreSQL logs for detailed error messages

## Performance Considerations

### Same Database
- ✅ Simpler configuration
- ✅ Single connection pool to manage
- ✅ Transactional consistency between app and audit
- ⚠️ Audit writes can impact application performance
- ⚠️ Single point of failure

### Separate Database
- ✅ Isolated performance (audit doesn't impact app)
- ✅ Independent scaling
- ✅ Different backup/retention policies
- ✅ Enhanced security (separate credentials)
- ⚠️ Slightly more complex configuration
- ⚠️ No cross-database transactions (eventual consistency)
