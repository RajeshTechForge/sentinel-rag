from typing import List, Tuple, Dict


class RbacManager:
    def __init__(self, rbac_config: Dict):
        self.access_matrix = rbac_config.get("access_matrix", {})

    def get_user_access_filters(self, user_id: str, db) -> List[Tuple[str, str]]:
        """
        Determines which (department, classification) pairs a user can access.
        """
        user_perms = db.get_user_role_and_department(user_id)

        if not user_perms:
            return []

        allowed_conditions = set()

        for dept, role in user_perms:
            for classification, dept_roles in self.access_matrix.items():
                if dept in dept_roles:
                    if role in dept_roles[dept]:
                        allowed_conditions.add((dept, classification))

        return list(allowed_conditions)
