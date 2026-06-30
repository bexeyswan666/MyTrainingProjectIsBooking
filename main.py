from fastapi import FastAPI
from routers.booking import router

app = FastAPI()

app.include_router(router)