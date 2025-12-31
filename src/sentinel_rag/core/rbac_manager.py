import json
import os
from typing import List, Tuple, Dict

from .exceptions import RbacConfigError


class RbacManager:
    def __init__(self, config_file: str = None):
        self.access_matrix = self._load_access_matrix(config_file)

    def _load_access_matrix(self, config_file: str = None) -> Dict:
        if config_file is None:
            raise RbacConfigError("Configuration file path is required.")

        if not os.path.exists(config_file):
            raise RbacConfigError(f"Configuration file not found at '{config_file}'.")

        try:
            with open(config_file, "r") as f:
                config = json.load(f)

            access_matrix = config.get("ACCESS_MATRIX")
            if not access_matrix:
                raise RbacConfigError(
                    f"ACCESS_MATRIX not found in configuration file: '{config_file}'."
                )

            return access_matrix
        
        except json.JSONDecodeError as e:
            raise RbacConfigError(
                f"Invalid JSON in configuration file: '{config_file}'."
            )
        except RbacConfigError:
            raise

        except Exception as e:
            raise RbacConfigError(
                f"Error loading access matrix from '{config_file}': {e}"
            )

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
