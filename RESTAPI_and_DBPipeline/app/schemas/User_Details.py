from pydantic import BaseModel, EmailStr
from typing import Optional, List

# Input model (what client sends)
class UserRegistration(BaseModel):
    FullName: str
    Email: EmailStr
    Organization: Optional[str]
    City: str
    Country: str
    PurposeOfUse: str
    Password: str

# Output model (what client receives)
class UserOut(BaseModel):
    ID: int
    Email: EmailStr
    FullName: str
    Approved: bool

    class Config:
        orm_mode = True
