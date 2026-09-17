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
    Search,
    ResponseCancell
)
from depencies import (get_current_user,
                       authenticate_user,
                       create_token,
                       get_current_admin,
                       get_booking_by_id,
                       get_room_by_id,
                       date_check)
router = APIRouter()

load_dotenv()


ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()


@router.post("/registration")
async def registration(response:Response,db:AsyncSession=Depends(get_db),user:CreateUser=Depends()):
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
    response.status_code = status.HTTP_201_CREATED
    return {"message":"You have registered"}




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



@router.get("/admin/search",tags=["admin"],dependencies=[Depends(get_current_admin)])
async def admin_get_search(search:Annotated[Search,Depends(Search)],db:AsyncSession=Depends(get_db)):
    sort_columns = {
    "price":"rooms.price",
    "username":"users.username",
    "date_from":"bookings.date_from",
    "date_to":"bookings.date_to"
    }
    sort_column = sort_columns[search.sort_by]
    order = search.sort_order.value
    result = await db.execute(text(f"""
                            SELECT users.id,users.username,users.email,hotels.city,bookings.date_from,bookings.date_to,bookings."status",
                            rooms.name,rooms.price,rooms.count_people
                            FROM bookings
                            JOIN users ON (bookings.user_id = users.id)
                            JOIN rooms ON (bookings.room_id = rooms.id)
                            JOIN hotels ON (rooms.hotel_id = hotels.id)
                            WHERE (CAST(:date_from AS DATE) IS NULL OR bookings.date_from >= :date_from)
                              AND (CAST(:date_to AS DATE) IS NULL OR bookings.date_to <= :date_to) 
                              AND (CAST(:status AS TEXT) IS NULL OR bookings."status" = :status)
                              AND (CAST(:username AS TEXT) IS NULL OR users.username LIKE :username)
                              AND (CAST(:city AS TEXT) IS NULL OR hotels.city LIKE :city)
                            ORDER BY {sort_column} {order}
                            LIMIT :limit
                            """),{"date_from":search.date_from if search.date_from else None,
                                  "date_to":search.date_to if search.date_to else None,
                                  "city":f"%{search.city}%" if search.city else None,
                                  "username":f"%{search.username}%" if search.username else None,
                                  "limit":search.limit,"status":search.status if search.status else None})
    return result.mappings().all()


@router.get("/admin/users",dependencies=[Depends(get_current_admin)],tags=["admin"])
async def get_users(db:AsyncSession = Depends(get_db)):
    res = await db.execute(text(
        """SELECT*
            FROM users"""
    )
    )
    return res.mappings().all()

@router.get("/admin/bookings",dependencies=[Depends(get_current_admin)],tags=["admin"])
async def booking_all(db:AsyncSession=Depends(get_db)):
    res = await db.execute(text(
                                    """SELECT bookings.id,bookings."status",bookings.date_from,bookings.date_to,users.username,
                                       users.email,rooms.name AS room_name,hotels.name AS hotel_name,hotels.city
                                       FROM bookings 
                                       JOIN rooms ON (bookings.room_id = rooms.id)
                                       JOIN hotels ON (rooms.hotel_id = hotels.id)
                                       JOIN users ON (bookings.user_id = users.id)"""
                                )
                            )
    return res.mappings().all()


@router.get("/users/me",response_model=UserResponse,tags=["users"])
def users_me_get(user:Annotated[User,Depends(get_current_user)]):
    return user

@router.get("/booking/my",response_model=list[BookingResponse],tags=["booking"])
async def booking_all(user:Annotated[User,Depends(get_current_user)],
                      db:AsyncSession=Depends(get_db)):
    res = await db.execute(text("""SELECT bookings.id,bookings."status",bookings.date_from,bookings.date_to,
                                   rooms.name AS room_name,hotels.name AS hotel_name,hotels.city
                                   FROM bookings 
                                   JOIN rooms ON (bookings.room_id = rooms.id)
                                   JOIN hotels ON (rooms.hotel_id = hotels.id)
                                   JOIN users ON (bookings.user_id = users.id)
                                   WHERE user_id = :user_id"""),{"user_id":user.id})
    result = res.mappings().all()
    return result

@router.get("/hotels")
async def get_hotels(db:AsyncSession=Depends(get_db)):
    res = await db.execute(text("""SELECT * FROM hotels"""))
    return res.mappings().all()

@router.post("/booking/{room_id}",tags=["booking"])
async def booking_create(response:Response,
                         room_id:Annotated[int,Path()],
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
    await date_check(room_id,booking.date_from,booking.date_to,db)
    result = await db.execute(text("""INSERT INTO bookings(user_id,room_id,status,date_from,date_to)
                             VALUES (:user_id,:room_id,'confirmed',:date_from,:date_to)
                             RETURNING id"""),
                             {"room_id":room_id,"user_id":user.id,
                            "date_to":booking.date_to,"date_from":booking.date_from})
    await db.commit()
    response.status_code = status.HTTP_201_CREATED
    return {"id":result.scalar_one(),
            "status":"confirmed"}

# date_to новым днем можно считать только следующий день от конца бронирования


@router.get("/hotels/rooms/{room_id}")
async def hotels_room_id(room_id:Annotated[int,Path()],db:AsyncSession=Depends(get_db)):
    room = await get_room_by_id(room_id,db)
    return room

@router.get("/rooms/{room_id}")
async def booking_room_id(room_id:Annotated[int,Path()],db:AsyncSession=Depends(get_db)):
    res = await db.execute(text("""SELECT rooms.name as rooms_name,hotels.name as hotels_name,hotels.city
                                    FROM rooms
                                    JOIN hotels ON (rooms.hotel_id = hotels.id)
                                    WHERE rooms.id = :room_id"""),{"room_id":room_id})
    result = res.mappings().first()
    if result:
        return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail="Not found")






@router.get("/booking/{id_booking}",response_model=BookingResponse,tags=["booking"])
async def my_booking(user:Annotated[User,Depends(get_current_user)],
                     id_booking:int,db:AsyncSession=Depends(get_db)):
    booking = await get_booking_by_id(user,id_booking,db)
    return booking

@router.delete("/booking/{id_booking}",dependencies=[Depends(get_current_admin)],tags=["admin"])
async def delete_booking(id_booking:Annotated[int,Path()],
                         user:Annotated[User,Depends(get_current_user)],
                         db:AsyncSession=Depends(get_db)):
    await get_booking_by_id(user,id_booking,db)
    await db.execute(text("""DELETE FROM bookings WHERE id = :id_booking"""),{"id_booking":id_booking})
    await db.commit()
    return {"status":"delete"}

@router.patch("/bookind/status/{id_bookind}",dependencies=[Depends(get_current_admin)],tags=["admin"])
async def patch_status_by_id(status:OptionsStatus,id_bookind:Annotated[int,Path()],
                             user:Annotated[User,Depends(get_current_user)],
                             db:AsyncSession=Depends(get_db)):
    await get_booking_by_id(user,id_bookind,db)
    await db.execute(text("""UPDATE bookings SET "status" = :status WHERE id = :id_booking"""),
                     {"status":status,"id_booking":id_bookind})
    await db.commit()
    return {"status":"update"}

@router.patch("/booking/{id_booking}/cancel")
async def patch_booking_cancel(
                               response:Response,
                               id_booking:Annotated[int,Path()],
                               user:Annotated[User,Depends(get_current_user)],
                               db:AsyncSession=Depends(get_db),
                               ):
    verification = await get_booking_by_id(user,id_booking,db)
    if verification.status == "cancelled":
        response.status_code = status.HTTP_409_CONFLICT
        return {"message":"Already canceled"}
    else:
        await db.execute(text("""UPDATE bookings SET "status" = 'cancelled' WHERE id = :id_booking"""),
                     {"id_booking":id_booking}) 
        await db.commit()
    return {"id":verification.id,
            "status":"cancelled"}
    

    


