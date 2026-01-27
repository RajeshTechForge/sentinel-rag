<div align="center">

# Sentinel RAG API - User Guide

</div>

<br>
<br>

Welcome to the Sentinel RAG API! This guide will help you get started with integrating our enterprise-grade RAG (Retrieval-Augmented Generation) system into your applications.

## Table of Contents

- [Quick Start](#-quick-start)
- [Authentication](#-authentication)
- [API Endpoints](#-api-endpoints)
- [Request & Response Formats](#-request--response-formats)
- [Error Handling](#-error-handling)
- [Example Workflows](#-example-workflows)
- [Best Practces](#-best-practices)


## ⚡ Quick Start

### 1. Prerequisites

- Active user account with valid credentials
- OIDC-compatible identity provider (Okta, Auth0, Azure AD, etc.)
- API access permissions according to your config file

### 2. Authentication Flow

```bash
# Step 1: Initiate OAuth login
curl -L http://localhost:8000/auth/login

# Step 2: User completes OIDC authentication in browser
# Step 3: Callback sets access_token cookie automatically
# Step 4: Use cookie for authenticated requests

# Alternative: Extract token from cookie for API clients
TOKEN="your-access-token"
curl -H "Cookie: access_token=$TOKEN" \
     http://localhost:8000/api/query
```

### 3. Your First Query

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=$TOKEN" \
  -d '{
    "user_query": "What are our security policies?",
    "k": 5
  }'
```


## 🔐 Authentication

### OAuth 2.0 / OIDC Flow

Sentinel RAG uses industry-standard OIDC for authentication.

#### Login

**Endpoint**: `GET /auth/login`

Redirects to your identity provider for authentication.

```bash
curl -L http://localhost:8000/auth/login
```

#### Callback

**Endpoint**: `GET /auth/callback`

Handles the OAuth callback and sets an HTTP-only secure cookie with your access token.

#### Logout

**Endpoint**: `POST /auth/logout`

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Cookie: access_token=$TOKEN"
```

**Response**:
```json
{
  "message": "Logged out successfully"
}
```

### Using Access Tokens

All authenticated endpoints require the `access_token` cookie:

```bash
# Include cookie in requests
curl -H "Cookie: access_token=$YOUR_TOKEN" \
     http://localhost:8000/api/v1/query
```

**Token Expiration**: Tokens expire after 60 minutes by default. Re-authenticate when expired.


## 📚 API Endpoints

### Health Checks

#### Basic Health Check

**Endpoint**: `GET /health`

Check if the API is running.

```bash
curl http://localhost:8000/health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "audit_enabled": true,
  "timestamp": "2026-01-07T10:30:00Z"
}
```

#### Detailed Health Check

**Endpoint**: `GET /health/ready`

Get detailed component health status.

```bash
curl http://localhost:8000/health/ready
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "connected": true
    },
    "engine": {
      "status": "healthy",
      "initialized": true
    },
    "audit": {
      "status": "healthy",
      "enabled": true
    }
  }
}
```


### User Management

#### Get User Information

**Endpoint**: `POST /api/user`

**Request**:
```bash
curl -X POST http://localhost:8000/api/user \
  -H "Cookie: access_token=$TOKEN" \
```

**Response**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_email": "john.doe@example.com",
  "full_name": "John Doe",
  "user_role": "analyst",
  "user_department": "engineering"
}
```

#### Get User's Documents

**Endpoint**: `POST /api/user/docs`

Get all documents uploaded by current user.

**Request**:
```bash
curl -X POST http://localhost:8000/api/user/docs \
  -H "Cookie: access_token=$TOKEN" \
```

**Response**:
```json
[
  {
    "doc_id": "doc-123",
    "title": "Security Policy v2",
    "classification": "confidential",
    "department": "engineering",
    "created_at": "2026-01-05T14:30:00Z"
  }
]
```


### Document Management

#### Upload Document

**Endpoint**: `POST /api/documents/upload`

Upload and process a document for RAG.

**Request** (multipart/form-data):
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Cookie: access_token=$TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "doc_title=Security Policy 2026" \
  -F "doc_description=Updated security guidelines" \
  -F "doc_department=engineering" \
  -F "doc_classification=confidential"
```

**Form Fields**:
- `file` (required): Document file (PDF, TXT, DOCX, etc.)
- `doc_title` (required): Document title (max 500 chars)
- `doc_description` (optional): Document description (max 2000 chars)
- `doc_department` (required): Department name
- `doc_classification` (required): One of: `public`, `internal`, `confidential`, `restricted`

**Response**:
```json
{
  "doc_id": "550e8400-e29b-41d4-a716-446655440001",
  "doc_classification": "confidential",
  "doc_department": "engineering",
  "uploaded_by": "john.doe@example.com",
  "processing_time_ms": 1234.56
}
```

**Status Codes**:
- `200`: Success
- `400`: Invalid department or classification
- `404`: User not found
- `422`: Validation error
- `500`: Processing error


### Query & Retrieval

#### Query Documents

**Endpoint**: `POST /api/query` 🔐 *Requires Authentication*

Perform semantic search across documents.

**Request**:
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=$TOKEN" \
  -d '{
    "user_query": "What are the password requirements?",
    "k": 5
  }'
```

**Request Body**:
```json
{
  "user_query": "Your search query",
  "k": 5  // Number of results (default: 5)
}
```

**Response**:
```json
[
  {
    "page_content": "Password requirements: minimum 12 characters...",
    "metadata": {
      "doc_id": "doc-123",
      "chunk_id": "chunk-456",
      "title": "Security Policy",
      "classification": "confidential",
      "department": "engineering"
    }
  }
]
```

**Access Control**:
- Users can only query documents from their department
- Classification level must match user's clearance
- Tenant isolation applies automatically

**PII Redaction**:
If PII is detected, it will be masked:
```
"Customer email: <EMAIL_ADDRESS> called about..."
```


## 🔗 Request & Response Formats

### Standard Response Structure

#### Success Response

```json
{
  "data": { ... },
  "metadata": {
    "timestamp": "2026-01-07T10:30:00Z"
  }
}
```

#### Error Response

All errors follow this format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "request_id": "req-123-456-789",
  "timestamp": "2026-01-07T10:30:00Z",
  "details": {
    // Additional error context
  }
}
```

### Common Data Types

#### Classification Levels
- `public`: Publicly accessible
- `internal`: Internal use only
- `confidential`: Confidential data
- `restricted`: Highly restricted

#### Date/Time Format
ISO 8601 UTC: `2026-01-07T10:30:00Z`


## 🗿 Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request succeeded |
| 400 | Bad Request | Invalid input parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Request validation failed |
| 429 | Rate Limited | Too many requests |
| 500 | Internal Error | Server error |
| 503 | Service Unavailable | System temporarily unavailable |

### Error Codes

#### Authentication Errors
- `AUTHENTICATION_FAILED`: Invalid credentials
- `UNAUTHORIZED`: Missing authentication
- `AUTHORIZATION_FAILED`: Insufficient permissions

#### Resource Errors
- `USER_NOT_FOUND`: User doesn't exist
- `DOCUMENT_NOT_FOUND`: Document doesn't exist
- `DEPARTMENT_NOT_FOUND`: Department doesn't exist

#### Validation Errors
- `VALIDATION_ERROR`: Input validation failed
- `QUERY_VALIDATION_ERROR`: Invalid query parameters

#### Processing Errors
- `DOCUMENT_PROCESSING_ERROR`: Document processing failed
- `QUERY_PROCESSING_ERROR`: Query execution failed

### Example Error Response

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "request_id": "req-abc-123",
  "timestamp": "2026-01-07T10:30:00Z",
  "details": {
    "validation_errors": [
      {
        "field": "doc_classification",
        "message": "Classification must be one of: public, internal, confidential, restricted",
        "type": "value_error"
      }
    ]
  }
}
```


## 🎩 Example Workflows

### Workflow 1: Document Upload and Query

```bash
# 1. Authenticate
curl -L http://localhost:8000/auth/login
# Complete OIDC flow in browser, obtain token

# 2. Upload a document
curl -X POST http://localhost:8000/api/documents/upload \
  -H "Cookie: access_token=$TOKEN" \
  -F "file=@company-policies.pdf" \
  -F "doc_title=Company Policies 2026" \
  -F "doc_description=Updated company policies" \
  -F "doc_department=hr" \
  -F "doc_classification=internal"

# Response: { "doc_id": "doc-123", ... }

# 3. Query the document
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=$TOKEN" \
  -d '{
    "user_query": "What is the remote work policy?",
    "k": 3
  }'
```

### Workflow 2: User Onboarding

```bash
# 1. New user completes OIDC authentication
curl -L http://localhost:8000/auth/login

# 2. Get available departments and roles
curl http://localhost:8000/auth/registration/options \
  -H "Cookie: registration_token=$TEMP_TOKEN"

# 3. Complete registration
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "registration_token": "temp-token-123",
    "role": "analyst",
    "department": "engineering"
  }'

# 4. User can now access the API
curl -X POST http://localhost:8000/api/user \
  -H "Cookie: access_token=$TOKEN" \
```

### Workflow 3: Audit Trail Review

```bash
# Check system health
curl http://localhost:8000/health/ready

# Verify audit logging is enabled
# Review logs via database queries (admin access required)
```


## 📌 Best Practices

### 1. Security

✅ **DO**:
- Always use HTTPS in production
- Store tokens securely (HTTP-only cookies recommended)
- Rotate secrets regularly
- Implement token refresh logic
- Validate all user inputs

❌ **DON'T**:
- Expose tokens in URLs or logs
- Share tokens between users
- Store tokens in localStorage (use secure cookies)
- Bypass authentication for testing in production

### 2. Performance

✅ **DO**:
- Cache frequently accessed data
- Use appropriate `k` values (5-10 for most queries)
- Implement client-side rate limiting
- Batch operations when possible
- Monitor query performance

❌ **DON'T**:
- Request excessive results (`k > 50`)
- Poll endpoints continuously
- Upload extremely large documents without chunking
- Make parallel requests excessively

### 3. Error Handling

```javascript
// Example: Robust error handling
async function queryDocuments(query) {
  try {
    const response = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',  // Include cookies
      body: JSON.stringify({
        user_query: query,
        k: 5
      })
    });

    if (!response.ok) {
      const error = await response.json();
      
      // Handle specific errors
      if (error.error === 'AUTHENTICATION_FAILED') {
        // Redirect to login
        window.location.href = '/auth/login';
      } else if (error.error === 'AUTHORIZATION_FAILED') {
        // Show permission error
        showError('You do not have access to this resource');
      } else {
        // Log error with request_id for debugging
        console.error(`Error ${error.error}: ${error.message}`, error.request_id);
      }
      
      return null;
    }

    return await response.json();
  } catch (err) {
    console.error('Network error:', err);
    return null;
  }
}
```


### 4. Query Optimization

```python
# ❌ Bad: Vague query
query = "documents"

# ✅ Good: Specific query
query = "What are the password complexity requirements in our security policy?"

# ❌ Bad: Requesting too many results
k = 100

# ✅ Good: Reasonable result count
k = 5  # or 10 for broader searches
```
