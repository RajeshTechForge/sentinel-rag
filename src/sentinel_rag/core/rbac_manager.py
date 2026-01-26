"""
Manages role-based access control (RBAC) for users based on their roles and departments.
Determines which (department, classification) pairs a user can access.
"""

from typing import Dict, FrozenSet, List, Tuple


class RbacManager:
    def __init__(self, rbac_config: Dict):
        self._access_matrix = rbac_config.get("access_matrix", {})
        # Pre-compute lookup structure: {(dept, role): {classifications}}
        self._role_permissions = self._build_permissions_index()

    def _build_permissions_index(self) -> Dict[Tuple[str, str], FrozenSet[str]]:
        """Build inverted index for O(1) permission lookups."""
        index = {}
        for classification, dept_roles in self._access_matrix.items():
            for dept, roles in dept_roles.items():
                for role in roles:
                    key = (dept, role)
                    if key not in index:
                        index[key] = set()
                    index[key].add(classification)
        return {k: frozenset(v) for k, v in index.items()}

    def get_user_access_filters(self, user_id: str, db) -> List[Tuple[str, str]]:
        """Get allowed (department, classification) pairs for user."""
        user_perms = db.get_user_role_and_department(user_id)
        if not user_perms:
            return []

        allowed = set()
        for dept, role in user_perms:
            classifications = self._role_permissions.get((dept, role), frozenset())
            for cls in classifications:
                allowed.add((dept, cls))

        return list(allowed)
