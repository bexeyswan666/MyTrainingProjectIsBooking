from fastapi import APIRouter,FastAPI,Body, Query,Path,Cookie,Header,Response,status,Form,File,UploadFile,HTTPException,Depends
from pydantic import BaseModel,Field,HttpUrl, EmailStr
from fastapi.responses import JSONResponse,RedirectResponse, HTMLResponse,PlainTextResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime, timedelta, timezone
import jwt
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from fastapi.encoders import jsonable_encoder
from typing import Annotated,Any
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
import os
from dotenv import load_dotenv
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date
from schemas.booking import (
    User,
    TokenData
)
from database import setting

SECRET_KEY = setting.SECRET_KEY
ALGORITHM = setting.ALGORITHM


password_hash = PasswordHash.recommended()

DUMMI_HASH = password_hash.hash("dummypassword")
oauth2_sheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_user_in_db(username,db):
    res = await db.execute(text("""SELECT * FROM users WHERE username =:username"""),
                           {"username":username})
    user = res.mappings().first()
    if user:
        return user

async def get_current_user(token:Annotated[str,Depends(oauth2_sheme)],
                           db:AsyncSession=Depends(get_db)):
    exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Coild not validate crenditales",
                            headers={"WWW-Authenticate":"bearer"})
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise exception
        token_data = TokenData(username=username)
        
    except InvalidTokenError:
        raise exception
    user = await get_user_in_db(token_data.username,db)
    if user is None:
        raise exception
    return user
    
def verify_user(password,hashed_password):
    return password_hash.verify(password,hashed_password)

async def authenticate_user(username,db,password):
    user = await get_user_in_db(username,db)
    if not user:
        return False
    if not verify_user(password,user.hashed_password):
        return False
    return user

def create_token(data:dict,expire_delta:timedelta):
    data_copy = data.copy()
    if expire_delta:
        expt =  datetime.now(timezone.utc)+expire_delta
    else:
        expt = datetime.now(timezone.utc)+timedelta(minutes=30)
    data_copy.update({"exp":expt})
    jwt_encode = jwt.encode(data_copy,SECRET_KEY,algorithm=ALGORITHM)
    return jwt_encode

def get_current_admin(user:Annotated[User,Depends(get_current_user)]):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access is denied")
    return user

async def date_check(room_id:int,date_from:date,date_to:date,db:AsyncSession):
    res = await db.execute(text("""SELECT * FROM bookings 
                                    WHERE bookings.room_id = :room_id AND 
                                    bookings.date_from < :date_to AND
                                    bookings.date_to >= :date_from AND
                                    "status" = 'confirmed'"""),
                                    {"date_to":date_to,"date_from":date_from,"room_id":room_id}) 
    result = res.mappings().first()
    if result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="The reservation for this date is already taken")
    
async def get_room_by_id(room_id:int,
                         db:AsyncSession):
    room = await db.execute(text(
            """SELECT * FROM rooms WHERE id =:room_id"""
    ),{"room_id":room_id})
    res_room = room.mappings().first()
    if res_room:
        return res_room
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail="Not found")


async def get_booking_by_id(user:User,
                            id_booking,
                            db:AsyncSession):
    if user.role == "admin":
        res = await db.execute(text("""SELECT bookings.id,bookings."status",bookings.date_from,bookings.date_to,users.username,
                                       users.email,rooms.name AS room_name,hotels.name AS hotel_name,hotels.city
                                       FROM bookings 
                                       JOIN rooms ON (bookings.room_id = rooms.id)
                                       JOIN hotels ON (rooms.hotel_id = hotels.id)
                                       JOIN users ON (bookings.user_id = users.id)
                                       WHERE bookings.id =:id_booking"""),
                                       {"id_booking":id_booking})
    else:
        res = await db.execute(text("""SELECT bookings.id,bookings."status",bookings.date_from,bookings.date_to,
                                       rooms.name AS room_name,hotels.name AS hotel_name,hotels.city
                                       FROM bookings 
                                       JOIN rooms ON (bookings.room_id = rooms.id)
                                       JOIN hotels ON (rooms.hotel_id = hotels.id)
                                       JOIN users ON (bookings.user_id = users.id)
                                       WHERE bookings.id = :id_booking AND user_id = :user_id"""),
                           {"id_booking":id_booking,"user_id":user.id})
    result = res.mappings().first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Not found")
    return result

async def get_booking_by_id_admin(id_booking,db:AsyncSession):
    res = await db.execute(text("""SELECT * FROM bookings WHERE bookings.id =:id_booking"""),
                           {"id_booking":id_booking})
    result = res.mappings().first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Not found")
    return result