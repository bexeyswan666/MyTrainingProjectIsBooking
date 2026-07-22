from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

class Setting(BaseSettings):
    DB_USER:str
    DB_PASSWORD:str
    DB_HOST:str
    DB_PORT:int
    DB_NAME:str

    SECRET_KEY:str
    ALGORITHM:str

    def DATABASE_URL(self)->str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    model_config = SettingsConfigDict(env_file=".env")

setting = Setting()

engine = create_async_engine(setting.DATABASE_URL(),echo = True)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session() as session:
        yield session