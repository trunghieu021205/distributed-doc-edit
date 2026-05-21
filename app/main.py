from fastapi import FastAPI

app = FastAPI(title="DocEdit Node")

@app.get("/")
async def root():
    return {"message": "Server is running"}