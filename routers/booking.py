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
    BookingResponse,
    Booking,
    CreateUser,
    User,
    UserInDb,
    Token,
    TokenData,
    UserResponse,
    OptionsStatus,
)
router = APIRouter()

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM","HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()

DUMMI_HASH = password_hash.hash("dummypassword")
oauth2_sheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/registration")
async def registration(db:AsyncSession=Depends(get_db),user:CreateUser=Depends()):
    hashed_password= password_hash.hash(user.password)
    username_ver = await db.execute(text("SELECT username FROM users WHERE username =:username OR email= :email"),
                                    {"username":user.username,"email":user.email})
    if username_ver.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Username or email is already in use.") 
    await db.execute(text("""
                            INSERT INTO users(username,email,hashed_password)
                            VALUES(:username,:email,:hashed_password)"""),
                            {"username":user.username,"email":user.email,"hashed_password":hashed_password})
    await db.commit()
    return {"message":"You have registered"}

async def get_user_in_db(username,db):
    res = await db.execute(text("""SELECT * FROM users WHERE username =:username"""),
                           {"username":username})
    user = res.mappings().first()
    if user:
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


@router.post("/token")
async def log_in_token(token:Annotated[OAuth2PasswordRequestForm,Depends()],
                       db:AsyncSession=Depends(get_db)):
    user = await authenticate_user(token.username,db,token.password)
    if not user :
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="invalid username or password",
                            headers={"WWW-Authenticate":"bearer"})
    access_token_expt = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_token(data={"sub":user.username,"role":user.role},expire_delta=access_token_expt)
    return Token(access_token=access_token,token_type="Bearer")

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

def get_current_admin(user:Annotated[User,Depends(get_current_user)]):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access is denied")
    return user


@router.get("/user/test",dependencies=[Depends(get_current_admin)])
async def get_users(db:AsyncSession = Depends(get_db)):
    res = await db.execute(text(
        """SELECT*
            FROM users"""
    )
    )
    return res.mappings().all()

@router.get("/booking/test",dependencies=[Depends(get_current_admin)])
async def booking_all(db:AsyncSession=Depends(get_db)):
    res = await db.execute(text("""SELECT * FROM bookings"""))
    return res.mappings().all()

@router.get("/users/me",response_model=UserResponse)
def users_me_get(user:Annotated[User,Depends(get_current_user)]):
    return user

@router.get("/booking/my",response_model=list[BookingResponse])
async def booking_all(user:Annotated[User,Depends(get_current_user)],
                      db:AsyncSession=Depends(get_db)):
    res = await db.execute(text("""SELECT * FROM bookings WHERE user_id = :user_id"""),{"user_id":user.id})
    result = res.mappings().all()
    return result

@router.get("/hotels")
async def get_hotels(db:AsyncSession=Depends(get_db)):
    res = await db.execute(text("""SELECT * FROM hotels"""))
    return res.mappings().all()

@router.post("/booking/{room_id}")
async def booking_create(room_id:Annotated[int,Path()],
                         user:Annotated[User,Depends(get_current_user)],
                         booking:Booking=Depends(),
                         db:AsyncSession=Depends(get_db)):
    if booking.date_from >= booking.date_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="date_to must be after date_from")
    if booking.date_from<date.today():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="date_from cannot be in the past")
    await get_room_by_id(room_id,db)
    await db.execute(text("""INSERT INTO bookings(user_id,room_id,status,date_from,date_to)
                             VALUES (:user_id,:room_id,'confirmed',:date_from,:date_to)"""),
                             {"room_id":room_id,"user_id":user.id,
                            "date_to":booking.date_to,"date_from":booking.date_from})
    await db.commit()
    return {"status":"create booking!"}
        
     
    
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

@router.get("/booking/room/{room_id}")
async def bookint_room_id(room_id:Annotated[int,Path()],db:AsyncSession=Depends(get_db)):
    room = await get_room_by_id(room_id,db)
    return room

async def get_booking_by_id(user,
                            id_booking,
                            db):
    res = await db.execute(text("""SELECT * FROM bookings WHERE bookings.id = :id_booking AND user_id = :user_id"""),
                           {"id_booking":id_booking,"user_id":user.id})
    result = res.mappings().first()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result

@router.get("/booking/{id_booking}",response_model=BookingResponse)
async def my_booking(user:Annotated[User,Depends(get_current_user)],
                     id_booking:int,db:AsyncSession=Depends(get_db)):
    booking = await get_booking_by_id(user,id_booking,db)
    return booking

@router.delete("/booking/{id_booking}",dependencies=[Depends(get_current_admin)])
async def delete_booking(id_booking:Annotated[int,Path()],
                         user:Annotated[User,Depends(get_current_user)],
                         db:AsyncSession=Depends(get_db)):
    await get_booking_by_id(user,id_booking,db)
    await db.execute(text("""DELETE FROM bookings WHERE id = :id_booking"""),{"id_booking":id_booking})
    await db.commit()
    return {"status":"delete"}

@router.patch("/bookind/status/{id_bookind}",dependencies=[Depends(get_current_admin)])
async def patch_status_by_id(status:OptionsStatus,id_bookind:Annotated[int,Path()],
                             user:Annotated[User,Depends(get_current_user)],
                             db:AsyncSession=Depends(get_db)):
    await get_booking_by_id(user,id_bookind,db)
    await db.execute(text("""UPDATE bookings SET "status" = :status WHERE id = :id_booking"""),
                     {"status":status,"id_booking":id_bookind})
    await db.commit()
    return {"status":"update"}

@router.patch("/booking/{id_booking}/cancel")
async def patch_booking_cancel(id_booking:Annotated[int,Path()],
                               user:Annotated[User,Depends(get_current_user)],
                               db:AsyncSession=Depends(get_db)):
    await get_booking_by_id(user,id_booking,db)
    await db.execute(text("""UPDATE bookings SET "status" = 'cancelled' WHERE id = :id_booking"""),
                     {"id_booking":id_booking})
    await db.commit()
    return {"ststus":"Update!"}

    


