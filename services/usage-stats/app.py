from fastapi import FastAPI
from test import test

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello from Docker on localhost:8000!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
