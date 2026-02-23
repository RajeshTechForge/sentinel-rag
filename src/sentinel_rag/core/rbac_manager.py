"""
Manages role-based access control (RBAC) for users based on their roles and departments.
Determines which (department, classification) pairs a user can access.
"""

from typing import Dict, FrozenSet, List, Tuple


class RbacManager:
    def __init__(self, db):
        self.db = db
        # Pre-compute lookup structure: {(dept, role): {classifications}}
        self._role_permissions = self._build_permissions_index()

    def _build_permissions_index(self) -> Dict[Tuple[str, str], FrozenSet[str]]:
        """Build inverted index for O(1) permission lookups."""
        index = {}
        role_access_list = self.db.get_all_role_access()

        for role, dept, access_level in role_access_list:
            key = (dept, role)
            if key not in index:
                index[key] = set()
            index[key].add(access_level)

        return {k: frozenset(v) for k, v in index.items()}

    def get_user_access_filters(self, user_id: str) -> List[Tuple[str, str]]:
        """Get allowed (department, classification) pairs for user."""
        user_perm = self.db.get_user_role_and_department(user_id)
        if not user_perm:
            return []

        allowed = set()
        dept, role = user_perm
        classifications = self._role_permissions.get((dept, role), frozenset())
        for cls in classifications:
            allowed.add((dept, cls))

        return list(allowed)

    def reload_permissions(self):
        """Reload permissions from database."""
        self._role_permissions = self._build_permissions_index()
