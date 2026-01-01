<div align="center">

# ⚖️ Compliance & Auditing Governance Framework

</div>

<br>
<br>

Sentinel RAG is engineered for industries where "I don't know" is not an acceptable answer to a data access query. This guide details how the framework satisfies global regulatory standards—including **GDPR, HIPAA, and SOC2**—through its automated audit infrastructure.


## 🏗️ The Auditing Architecture

Sentinel RAG employs a multi-layered observability approach to ensure a complete chain of custody for every data interaction.

| Component | Responsibility | Implementation |
| --- | --- | --- |
| **Request Middleware** | Captures every API interaction, latency, and status code. | `AuditLoggingMiddleware` |
| **Functional Decorators** | Deep-dive auditing for specific data modifications or access checks. | `@audit_data_access`, `@audit_modification` |
| **Central Audit Service** | Type-safe persistence layer using PostgreSQL. | `AuditService` (AsyncPG + Pydantic) |
| **Schema Layer** | Relational integrity between users, roles, and access logs. | `schema.sql` |


## 📋 Regulatory Compliance Matrix

### 1. GDPR (General Data Protection Regulation)

**Focus:** Data Subject Rights and Processing Transparency.

* **Article 30 (Processing Records):** Every query and ingestion is logged with `resource_type` and `event_category`.
* **Article 15 (Right of Access):** The `get_user_activity` method provides a comprehensive export of all actions performed by a specific UUID.
* **Article 17 (Right to Erasure):** The `modification_audit` table captures `DELETE` operations, providing proof of data removal.
* **PII Sanitization:** The system automatically flags `pii_accessed: True` when the redaction engine triggers, ensuring compliance with data minimization principles.

### 2. HIPAA (Health Insurance Portability and Accountability Act)

**Focus:** Technical Safeguards for Protected Health Information (ePHI).

* **§164.312(b) Audit Controls:** Sentinel RAG records and examines activity in systems that contain ePHI.
* **Access Context:** Every log entry denormalizes `department_name`, `role_name`, and `classification_level` at the time of access to prevent "stale metadata" reporting.

### 3. SOC 2 (Security, Availability, Processing Integrity)

**Focus:** Logical Access Monitoring.

* **CC6.1 (Authorized Access):** `AuthAuditEntry` tracks every login attempt, MFA usage, and account lock events.
* **PI1.4 (Processing Integrity):** The `query_audit` table logs `vector_search_time_ms` and `chunks_filtered`, proving that the RBAC engine successfully pruned unauthorized data from the LLM context.


## 🛠️ Implementation Guide

### Automated Request Logging

The framework utilizes FastAPI middleware to capture the "Who, What, Where, and When" of every request without manual instrumentation.

```python
# app.py integration
app.add_middleware(AuditLoggingMiddleware, audit_service=audit_service)

```

### Granular Data Auditing

For sensitive operations, use the built-in decorators to capture the state before and after modifications.

```python
@audit_modification(table_name="documents", operation="UPDATE")
async def update_doc_metadata(doc_id: UUID, updates: dict, audit_service: AuditService):
    # The decorator handles the logging of log_id and changes
    return await db.update(doc_id, updates)

```


## 🔍 Compliance Query Library

Sentinel RAG ships with optimized GIN indexes on JSONB fields to ensure compliance reports remain performant even with millions of rows.

### Detect "Brute-Force" Access Patterns

This query identifies users attempting to access documents they don't have permissions for.

```sql
SELECT 
    user_email, ip_address, COUNT(*) as failed_attempts
FROM audit_logs
WHERE outcome = 'failure' 
  AND event_category = 'authorization'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY user_email, ip_address
HAVING COUNT(*) > 10;

```

### PII Access Audit Trail (GDPR/HIPAA)

Generate a list of all instances where sensitive data was handled.

```sql
SELECT 
    timestamp, user_email, resource_name, pii_types
FROM audit_logs
WHERE pii_accessed = TRUE
ORDER BY timestamp DESC;

```


## 🗄️ Retention & Archival Strategy

Sentinel-RAG supports **Declarative Partitioning** and automated retention policies.

 1. **Retention Mapping:** Use `get_retention_years(classification)` to set TTLs (Time-to-Live) based on data sensitivity (e.g., Confidential = 7 years).

 2. **Archival:** The `archive_old_logs` method marks records as `archived=TRUE`, allowing for data to be moved to cold storage (like AWS S3 or Glacier) while maintaining a pointer in the primary database.


## 🔐 Security Best Practices

> [!IMPORTANT]
> **Audit logs are high-value targets for attackers.** > * **Immutable Logs:** Sentinel RAG's `AuditService` is designed to be **Append-Only**. There are no `UPDATE` methods provided for the audit tables.
> * **Isolation:** In production, we recommend using a dedicated PostgreSQL schema or even a separate database instance for audit logs to prevent cross-contamination during a breach.
> * **Integrity:** Consider enabling PostgreSQL's `log_checkpoints` and file-system level encryption (TDE) for the audit partitions.
> 

---

<div align="center">
<p><b>Sentinel RAG</b>
<br>Turning compliance from a bottleneck into a competitive advantage ❤️</p>
</div>
