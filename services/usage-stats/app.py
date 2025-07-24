import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.macrostrat import get_macrostrat_data
from src.rockd import get_rockd_data
import logging



@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()

    async def periodic_task():
        while not stop_event.is_set():
            try:
                await get_rockd_data()
                await get_macrostrat_data()
            except Exception as e:
                logging.exception("Error in periodic task: %s", e)

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                pass  

    task = asyncio.create_task(periodic_task())
    yield
    stop_event.set()
    await task


app = FastAPI(lifespan=lifespan)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
