from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import test

@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()

    async def periodic_task():
        while not stop_event.is_set():
            await test.run_task()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=2.0)
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
