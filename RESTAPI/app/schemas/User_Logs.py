from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserLogEntry(BaseModel):
    ID: int
    User_ID: int
    Module: str
    Action: Optional[str] = None
    Result: Optional[str] = None
    Details: Optional[str] = None

class UserLogOut(UserLogEntry):
    id: int

    class Config:
        orm_mode = True
