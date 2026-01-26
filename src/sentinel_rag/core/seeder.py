"""
Seeder module to populate initial data into the database.
Reads RBAC config and creates missing departments and roles.
"""

from typing import Dict

from .exceptions import SeederError


def seed_initial_data(db=None, rbac_config: Dict = None):
    """Seed database with departments and roles from RBAC config."""
    if db is None:
        raise SeederError("Database instance is required")

    rbac_config = rbac_config or {}

    # Seed departments
    existing_depts = set(db.get_all_departments())
    new_depts = [
        d for d in rbac_config.get("departments", []) if d not in existing_depts
    ]

    for dept_name in new_depts:
        try:
            db.create_department(dept_name)
        except Exception as e:
            raise SeederError(f"Failed to create department '{dept_name}': {e}") from e

    # Seed roles
    existing_roles = {
        (r["role_name"], r["department_name"]) for r in db.get_all_roles()
    }
    roles_map = rbac_config.get("roles", {})

    for dept_name, roles in roles_map.items():
        for role_name in roles:
            if (role_name, dept_name) not in existing_roles:
                try:
                    db.create_role(role_name, dept_name)
                except Exception as e:
                    raise SeederError(
                        f"Failed to create role '{role_name}' in '{dept_name}': {e}"
                    ) from e
