from pydantic import BaseModel,Field
import datetime
from enum import Enum
class BookingResponse(BaseModel):
    id:int
    user_name:str=Field(min_length = 2 ,max_length = 50)
    room_name:str
    date:datetime.date
    status:str

class BookingCreate(BaseModel):
    user_name:str = Field(min_length = 2 , max_length = 50)
    room_name:str
    date: datetime.date
    status:str = Field(default = "pinding")

class BookingPut(BaseModel):
    user_name:str  
    room_name:str 
    date:datetime.date
    status:str

class BookingPatch(BaseModel):
    hotel_name:str | None = None
    #user_name:str | None = None
    #room_name:str | None = None
    #date:datetime.date | None = None
    #status:str | None = None

class SearchByFilter:
    def __init__(self,owner: str | None = None , hotel_name:str | None = None):
        self.owner = owner
        self.hotel_name = hotel_name


class OptionsStatus(str,Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"

class StatusPatch(BaseModel):
    status:OptionsStatus

class CreateUser(BaseModel):
    username:str
    password:str
    

class User(BaseModel):
    username:str
    role:str|None=None
    
class UserInDb(User):
    hashed_password:str

class Token(BaseModel):
    access_token:str
    token_type:str

class TokenData(BaseModel):
    username:str

class BookingCreateHostel(BaseModel):
    hotel_name:str
    

