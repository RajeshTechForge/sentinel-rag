<div align="center">

# Configuration & Security Policy

</div>

<br>
<br>

Sentine lRAG is built on the principle of **Least Privilege**. This document outlines how to configure the Role-Based Access Control (RBAC) system, define data classifications, and integrate these policies into the Sentinel engine.

## 🏗️ Core Concepts

Before modifying the configuration, it is important to understand the three pillars of Sentinel-RAG's security model:

1. **Departments:** Logical boundaries for your organization (e.g., `engineering`, `finance`).
2. **Roles:** Specific job functions within a department (e.g., `intern`, `manager`).
3. **Access Matrix:** The mapping that defines which **Role** in which **Department** can see which **Classification** of data.

---

## 📄 The `config.json` File

The configuration file is the heart of the `RbacManager`. It defines your organization’s structure. By default, the system looks for the path defined in the `SENTINEL_CONFIG_PATH` environment variable.

### Structure Breakdown

```json
{
    "DEPARTMENTS": ["finance", "engineering"],
    "ROLES": {
        "engineering": ["intern", "engineer", "senior_engineer"]
    },
    "ACCESS_MATRIX": {
        "confidential": {
            "engineering": ["senior_engineer"]
        }
    }
}

```

### Classification Levels

The keys inside `ACCESS_MATRIX` (e.g., `public`, `internal`, `confidential`) represent the **sensitivity** of your documents.

* **Public:** Accessible by almost everyone across departments.
* **Internal:** General employee data, restricted to specific departments.
* **Confidential:** Highly sensitive; usually restricted to Management or Senior roles.

---

## ⚖️ The Access Matrix Logic

The `RbacManager` determines access using an **Intersection Filter**. When a user performs a query, the system identifies all allowed `(department, classification)` pairs.

| Document Classification | Department | Allowed Roles |
| --- | --- | --- |
| **Public** | Any | All roles listed in the `public` block. |
| **Internal** | Engineering | `engineer`, `senior_engineer`, `engineering_manager` |
| **Confidential** | Engineering | `engineering_manager` |

> [!NOTE]
> If a user holds multiple roles across different departments, Sentinel RAG aggregates the permissions, allowing the user to see the union of all authorized documents.

---

## 🛠️ Implementation & Integration

### 1. Environment Configuration

To point Sentinel RAG to your custom security policy, update your `.env` file:

```bash
# Path to your custom rbac_config.json
SENTINEL_CONFIG_PATH="/app/configs/my_org_policy.json"

```

### 2. How the Code Loads Config

The `RbacManager` is responsible for parsing this JSON and validating its structure. If the `ACCESS_MATRIX` is missing or the JSON is malformed, the system will raise a `RbacConfigError` at startup, preventing a "fail-open" security state.

### 3. Dynamic Filtering in Queries

When you call the `/query` endpoint, the following sequence occurs:

1. **Identity Check:** The system fetches the `user_id` and their associated roles from the DB.
2. **Filter Generation:** `RbacManager.get_user_access_filters()` generates a list of allowed metadata tags.
3. **Vector Search:** These tags are injected into the `pgvector` query.
4. **Result:** The database **only** returns chunks that match the user's allowed classification and department.

---

## 🛡️ Best Practices for Production

* **Immutable Config:** In production (Docker/K8s), mount the `config.json` as a read-only volume.
* **Audit Enabled:** Ensure `ENABLE_AUDIT_LOGGING` is set to `True` in your `app.py`. This ensures that even if a user is granted access, their query and the retrieved documents are logged for compliance.
* **Fail-Closed Design:** If a user’s role or department cannot be found in the database, `get_user_access_filters` returns an empty list `[]`, resulting in zero documents being retrieved.

---

## 🚦 Troubleshooting

| Issue | Potential Cause | Solution |
| --- | --- | --- |
| `RbacConfigError` | Missing `ACCESS_MATRIX` key. | Ensure your JSON exactly matches the structure in the example. |
| Empty Query Results | User role mismatch. | Check if the user's role in the DB matches a role string in `config.json`. |
| `FileNotFoundError` | Incorrect path in `.env`. | Verify the `SENTINEL_CONFIG_PATH` absolute path. |
