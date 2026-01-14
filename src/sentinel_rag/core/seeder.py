from typing import Dict

from .exceptions import SeederError


def seed_initial_data(db=None, rbac_config: Dict = {}):
    """
    Reads config.json and populates the database with
    departments and roles if they don't already exist.

    Raises:
        ConfigSeedError: If required parameters are missing or file is invalid
    """

    if db is None:
        raise SeederError("Database instance is required")

    #        Fill Departments
    # ------------------------------
    existing_depts = set(db.get_all_departments())
    target_depts = rbac_config.get("DEPARTMENTS", [])

    for dept_name in target_depts:
        if dept_name not in existing_depts:
            try:
                db.create_department(dept_name)
            except Exception as e:
                raise SeederError(f"Error creating department '{dept_name}': {e}")

    #         Fill Roles
    # ------------------------------
    existing_roles_data = db.get_all_roles()
    existing_role_dept_pairs = {
        (r["role_name"], r["department_name"]) for r in existing_roles_data
    }

    roles_map = rbac_config.get("ROLES", {})

    for dept_name, roles_list in roles_map.items():
        for role_name in roles_list:
            if (role_name, dept_name) not in existing_role_dept_pairs:
                try:
                    db.create_role(role_name, dept_name)
                except Exception as e:
                    raise SeederError(
                        f"Error creating role '{role_name}' in department '{dept_name}': {e}"
                    )
