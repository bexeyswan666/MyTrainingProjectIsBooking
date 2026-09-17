from fastapi import FastAPI
from routers.booking import router
from task import lifespan
tags_metadata = [{
    "name":"users","description":"Operatipns with users.",
},
{"name":"booking","description":"Operatipns with booking."}
,{"name":"admin","description":"Operatipns with admin."}]


app = FastAPI(lifespan=lifespan,title="Booking API",
              description="API for hotel booking service.",
              version="1.0.0",
              openapi_tags=tags_metadata)

app.include_router(router)