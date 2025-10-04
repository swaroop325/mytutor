from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class User(BaseModel):
    id: str
    username: str
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# In-memory storage with pre-configured admin user
# Password: admin123
users_db: dict[str, User] = {
    "admin": User(
        id="admin-001",
        username="admin",
        hashed_password="$2b$12$vkFmNPxpZa54iKenYcZ2tuT2DsSlmBvvTykJR78o/1WGKN3OOrNbe",
        created_at=datetime(2025, 1, 1)
    )
}
