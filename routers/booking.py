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
from schemas.booking import (
    BookingCreate,
    BookingResponse,
    BookingPatch,
    BookingPut,
    SearchByFilter,
    StatusPatch,
    CreateUser,
    User,
    UserInDb,
    Token,
    TokenData,
    BookingCreateHostel,
)
router = APIRouter()

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM","HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()

DUMMI_HASH = password_hash.hash("dummypassword")
oauth2_sheme = OAuth2PasswordBearer(tokenUrl="token")

DB_Reservation_room = []

DB_Users = {"admin": {
        "username": "admin",
        "role":"admin",
        "hashed_password":"$argon2id$v=19$m=65536,t=3,p=4$M7VamS8pwGd4mwBCYA3loQ$fnL+VvEP6hE6sp/6gon2QmYQIWQhr3sJDQqe9WOWv5M"
    }}

# def booking_get(id:int):
#     booking = next((i for i in DB_Reservation_room if i["id"] == id),None)
#     if booking is None:
#         raise HTTPException(status_code=404,detail="not found")
#     return booking

# @router.post("/booking/",response_model=BookingResponse,summary="создать запись",
#           status_code=201,
#           description="создание записи бронирования и присваевания этой записи уникального id")
# def reservation_creation(create_reservat:BookingCreate):
#      existing_booking = next((i for i in DB_Reservation_room if i["room_name"] == create_reservat.room_name and i["date"] == create_reservat.date),None)
#      if existing_booking is not None:
#         raise HTTPException(status_code=409,detail="Комната или дата на этот день заняты!")
#      reservat_dict = create_reservat.model_dump()
#      id = len(DB_Reservation_room)+1
#      reservat_dict["id"] = id
#      DB_Reservation_room.append(reservat_dict)
#      return reservat_dict

# @router.get("/booking/search",response_model=list[BookingResponse])
# def booking_search_filter(filter:Annotated[SearchByFilter,Depends()]):
#     res = []
#     for booking in DB_Reservation_room:
#         if filter.user_name and filter.user_name.lower() not in booking["user_name"].lower():
#             continue
#         if filter.room_name and filter.room_name.lower() not in booking["room_name"].lower():
#             continue
#         res.append(booking)
#     return res

#@router.get("/booking/{id}",response_model=BookingResponse,
#         summary="найти запись по id"
#         ,status_code=200,
#        
#         description="нахождение в базе записи по уникальному id")
#def searc_booking_id(bokin=Depends(booking_get)):
#    return bokin
    

# @router.get("/booking/",response_model=list[BookingResponse]
#          ,summary="показать все запси booking"
#         ,
#         description="просмотр всех существующих записей")
# def bookings_all():
#     return DB_Reservation_room


# @router.delete("/booking/{id}",summary="удаление записи по id",
            
#             description="удаление записи по уникальному id если эта запись вообще есть в базе")
# def delete_booking(bokin=Depends(booking_get)):
#     DB_Reservation_room.remove(bokin)
#     return {"status":"delete"}

# @router.put("/booking/{id}",response_model=BookingResponse)
# def put_booking(new_data:BookingPut,booking=Depends(booking_get)):
#    new_data_dict = new_data.model_dump()
#    new_data_dict["id"] = booking["id"]
#    booking.update(new_data_dict)
#    return booking


# @router.patch("/booking/{id}",response_model=BookingResponse)
# def patch_booking(new_data:BookingPatch,booking=Depends(booking_get)):
#     new_data_dict = new_data.model_dump(exclude_unset=True)
#     booking.update(new_data_dict)
#     return booking

# @router.patch("/bookig/{id}/status",response_model=BookingResponse)
# def patch_booking_status(status:StatusPatch,booking=Depends(booking_get)):
#     data_dict = status.model_dump()
#     if booking["status"] == "cancelled":
#         raise HTTPException(status_code=400,detail="Changes are not allowed")
#     booking.update(data_dict)
#     return booking

def get_user_in_db(db,username):
    if username in db:
        user = db[username]
        return UserInDb(**user)
    
def verify_user(password,hashed_password):
    return password_hash.verify(password,hashed_password)

def authenticate_user(username,db,password):
    user = get_user_in_db(db,username)
    if not user:
        print("не нашли в бд")
        return False
    if not verify_user(password,user.hashed_password):
        print("не прошли верификацию")
        return False
    return user

def create_token(data:dict,expire_delta:timedelta):
    data_copy = data.copy()
    if expire_delta:
        expt = datetime.now(timezone.utc)+expire_delta
    else:
        expt = datetime.now(timezone.utc)+timedelta(minutes=30)
    data_copy.update({"exp":expt})
    jwt_encode = jwt.encode(data_copy,SECRET_KEY,algorithm=ALGORITHM)
    return jwt_encode

def get_current_user(token:Annotated[str,Depends(oauth2_sheme)]):
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
    user = get_user_in_db(DB_Users,token_data.username)
    if user is None:
        raise exception
    return user

def get_current_admin(user:Annotated[User,Depends(get_current_user)]):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access is denied")
    return user

def get_booking(id_booking:int):
    booking = next((i for i in DB_Reservation_room if i["id"] == id_booking),None)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"not found {id_booking}")
    return booking
 
@router.post("/token")
def log_in_token(token:Annotated[OAuth2PasswordRequestForm,Depends()]):
    user = authenticate_user(token.username,DB_Users,token.password)
    if not user :
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="invalid username or password",
                            headers={"WWW-Authenticate":"bearer"})
    access_token_expt = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_token(data={"sub":user.username,"role":user.role},expire_delta=access_token_expt)
    return Token(access_token=access_token,token_type="bearer")
@router.get("/users/me")
def users_me_get(user:Annotated[User,Depends(get_current_user)]):
    return user

@router.post("/registration")
def registration(user:CreateUser=Depends()):
    passwordhash = password_hash.hash(user.password)
    default_role = "user"
    if user.username in DB_Users:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"A user with the nickname {user.username} already exists in the system.")
    
    DB_Users.update({user.username:{"username":user.username,"role":default_role,
               "hashed_password":passwordhash}})
    return {"message":"You have registered"}

@router.post("/booking/hotel")
def booking_hotel(user:Annotated[User,Depends(get_current_user)],hotel:BookingCreateHostel):
    booking_id = len(DB_Reservation_room)+1
    result = {"id":booking_id,"hotel_name":hotel.hotel_name,"owner":user.username}
    DB_Reservation_room.append(result)
    return result 

@router.get("/my/booking")
def bookig_hotel(user:Annotated[User,Depends(get_current_user)]):
    res = []
    for i in DB_Reservation_room:
        if i["owner"] == user.username:
            res.append(i)
    return res    

@router.get("/booking/all",dependencies=[Depends(get_current_admin)])
def booking_all(owner:Annotated[str|None,Query()]=None,hotel_name:Annotated[str|None,Query()]=None):
    result = []
    for i in DB_Reservation_room:
        if owner is not None and owner.lower() not in i["owner"].lower():
            continue
        if hotel_name is not None and hotel_name.lower() not in i["hotel_name"].lower():
            continue
        result.append(i)
    return result

@router.delete("/booking/{id_booking}")
def delete_booking_id(user:Annotated[User,Depends(get_current_user)],
                      booking=Depends(get_booking)):
    if booking["owner"] != user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access is denied")
    else:
        DB_Reservation_room.remove(booking)
        return {"status":"delete"}
    
    # for i in DB_Reservation_room:
    #     if i["id"] == id_booking:
    #         if i["owner"] != user.username:
    #              raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
    #                         detail="Access is denied")
    #         else:
    #             DB_Reservation_room.remove(i)
    #             return {"status":"delete"}
    # else:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
    #                         detail=f"not found {id_booking}")
    
@router.get("/booking/{id_booking}")
def get_booking_id(user:Annotated[User,Depends(get_current_user)],
                   booking=Depends(get_booking)):
    if booking["owner"] != user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access is denied")
    return booking

@router.patch("/booking/{id_booking}")
def patch_booking_id(new_data:BookingPatch,user:Annotated[User,Depends(get_current_user)],booking=Depends(get_booking)):
    if booking["owner"] != user.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access is denied")
    new_data_dict = new_data.model_dump(exclude_unset=True)
    booking.update(new_data_dict)
    return booking
    
    


    