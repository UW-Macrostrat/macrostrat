from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from src.macrostrat import get_macrostrat_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()

    async def periodic_task():
        while not stop_event.is_set():
            await get_macrostrat_data()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                pass

    task = asyncio.create_task(periodic_task())
    yield  
    stop_event.set()
    await task  

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    return {"message": "Hello from Docker on localhost:8000!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
