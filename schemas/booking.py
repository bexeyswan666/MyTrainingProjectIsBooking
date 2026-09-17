from pydantic import BaseModel,Field
from datetime import date 
from enum import Enum
from pydantic import EmailStr


class BookingResponse(BaseModel):
    id:int
    status:str
    date_from:date
    date_to:date
    room_name:str
    hotel_name:str
    city:str
    username:str|None=None
    email:EmailStr|None=None

class ResponseCancell(BaseModel):
    booking_id:int
    date_from:date
    date_to:date
    room_name:str
    hotel_name:str
    city:str
    
class OptionsStatus(str,Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"

class OptionsSortOrder(str,Enum):
    ASC = "ASC"
    DESC = "DESC"

class OptionsSortBy(str,Enum):
    price = "price"
    username = "username"
    date_from = "date_from"
    date_to = "date_to"

class Search(BaseModel):
    username: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    city: str | None = None
    status: OptionsStatus | None = None
    limit: int
    sort_order:OptionsSortOrder
    sort_by:OptionsSortBy


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
    

class UserResponse(BaseModel):
    username:str
    email:EmailStr
    role:str

class User(BaseModel):
    id:int
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
    room_id:int
    date_from:date
    date_to:date

class BookingInDb(Booking):
    id:int
    user_id:int
    status:OptionsStatus
