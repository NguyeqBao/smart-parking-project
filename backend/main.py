from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine
from routers import slots, nodes, reservations, suggestion
from scheduler import start_scheduler
from mqtt_client import start_mqtt

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Parking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(slots.router)
app.include_router(nodes.router)
app.include_router(reservations.router)
app.include_router(suggestion.router)


@app.on_event("startup")
def on_startup():
    print("Server is starting...")
    start_scheduler()
    start_mqtt()


@app.get("/")
def root():
    return {"message": "Welcome to Smart Parking Backend"}