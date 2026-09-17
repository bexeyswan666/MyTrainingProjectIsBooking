from fastapi import APIRouter,FastAPI,HTTPException,Depends
from pydantic import BaseModel,Field,HttpUrl, EmailStr
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date
from contextlib import asynccontextmanager
import asyncio
from database import async_session


async def update_expired_reservation(db:AsyncSession):
    await db.execute(text("""UPDATE bookings
                        SET "status" = 'completed'
                        WHERE bookings.date_to < :today 
                        AND bookings."status" = 'confirmed'"""),
                        {"today":date.today()})
    await db.commit()


async def task_expire_reserv():
    while True:
        async with async_session() as session:
            await update_expired_reservation(session)
        await asyncio.sleep(86400)
            
        
        
@asynccontextmanager
async def lifespan(app:FastAPI):
    exp_res = task_expire_reserv()
    task = asyncio.create_task(exp_res)
    yield
    task.cancel()

        
