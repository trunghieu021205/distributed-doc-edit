# app/main.py
from fastapi import FastAPI
import database
import models   # đảm bảo models được load để Base biết
from database import engine, Base

app = FastAPI(title="Distributed Doc Editor", version="0.1.0")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
async def root():
    return {"message": "Distributed Doc Editor API is running"}