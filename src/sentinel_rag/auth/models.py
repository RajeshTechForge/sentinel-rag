from pydantic import BaseModel
from typing import List, Optional

class UserContext(BaseModel):
    user_id: str
    email: str
    tenant_id: str
    roles: List[str]
    department: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None
    tenant_id: str | None = None
