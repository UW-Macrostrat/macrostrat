import asyncio
from src.macrostrat import get_macrostrat_data
from src.rockd import get_rockd_data

async def periodic_task(stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await get_rockd_data()
            await get_macrostrat_data()
        except Exception:
            pass
        
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=10)
        except asyncio.TimeoutError:
            pass

async def main():
    stop_event = asyncio.Event()

    # Optionally handle graceful shutdown on signals
    loop = asyncio.get_running_loop()
    for sig in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, sig), stop_event.set)

    await periodic_task(stop_event)

if __name__ == "__main__":
    import signal
    asyncio.run(main())
