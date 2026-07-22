from pydantic import BaseModel,Field
from datetime import date 
from enum import Enum
from pydantic import EmailStr
class BookingResponse(BaseModel):
    id:int
    user_name:str=Field(min_length = 2 ,max_length = 50)
    room_name:str
    date:date
    status:str

class BookingCreate(BaseModel):
    user_name:str = Field(min_length = 2 , max_length = 50)
    room_name:str
    date: date
    status:str = Field(default = "pinding")

class BookingPut(BaseModel):
    user_name:str  
    room_name:str 
    date:date
    status:str

class BookingPatch(BaseModel):
    hotel_name:str | None = None
    #user_name:str | None = None
    #room_name:str | None = None
    #date:date | None = None
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
    email:EmailStr
    

class Token(BaseModel):
    access_token:str
    token_type:str

class TokenData(BaseModel):
    username:str

class BookingCreateHostel(BaseModel):
    hotel_name:str

class User(BaseModel):
    user_id:int
    username:str
    email:EmailStr
    role:str|None=None

class UserInDb(User):
    hashed_password:str
    
class BookingHotel(BaseModel):
    id:int
    name_hotel:str
    city:str
    description:str|None=None

class BookingRoom(BaseModel):
    id:int
    hotel_id:int
    name:str
    price:int
    count_people:int

class Booking(BaseModel):
    id:int
    user_id:int
    room_id:int
    date_from:date
    date_to:date
    status:OptionsStatus
