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

    #     Seed Departments
    # ---------------------------
    existing_depts = set(db.get_all_departments())
    new_depts = [
        d for d in rbac_config.get("departments", []) if d not in existing_depts
    ]

    for dept_name in new_depts:
        try:
            db.create_department(dept_name)
        except Exception as e:
            raise SeederError(f"Failed to create department '{dept_name}': {e}") from e

    #       Seed Roles
    # ---------------------------
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
                
    #    Seed Permission Levels
    # -------------------------------
    permission_levels = rbac_config.get("permission_levels", [])
    existing_permission_levels = set(db.get_all_permission_levels())

    for level_name in permission_levels:
        if level_name not in existing_permission_levels:
            try:
                db.create_permission_level(level_name)
            except Exception as e:
                raise SeederError(
                    f"Failed to create permission level '{level_name}': {e}"
                ) from e

    #    Seed Access Levels
    # -------------------------------
    access_matrix = rbac_config.get("access_matrix", {})
    existing_levels = set(db.get_all_access_levels())

    for level_name in access_matrix.keys():
        if level_name not in existing_levels:
            try:
                db.create_access_level(level_name)
            except Exception as e:
                raise SeederError(
                    f"Failed to create access level '{level_name}': {e}"
                ) from e

    #    Seed Role Access
    # -------------------------------
    existing_access = set(db.get_all_role_access())

    for level_name, departments in access_matrix.items():
        for department_name, roles in departments.items():
            for role_name in roles:
                if (role_name, department_name, level_name) not in existing_access:
                    try:
                        db.assign_role_access(role_name, department_name, level_name)
                    except Exception as e:
                        raise SeederError(
                            f"Failed to assign access '{level_name}' to role '{role_name}' in '{department_name}': {e}"
                        ) from e
