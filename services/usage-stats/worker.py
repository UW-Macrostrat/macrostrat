import asyncio
import os
import signal
import time
import traceback

from dotenv import load_dotenv
from src.macrostrat import get_macrostrat_data
from src.rockd import get_rockd_data

load_dotenv()


def get_env_var(name: str, timeout: int = 30) -> str:
    """
    Attempt to retrieve an environment variable `name`.
    Waits up to `timeout` seconds, checking every 1 second,
    before raising an error if the variable is still not set.
    """
    for _ in range(timeout):
        value = os.getenv(name)
        if value:
            print(f"[DEBUG] {name} found")
            return value
        print(f"[DEBUG] Waiting for environment variable {name}...")
        time.sleep(1)
    raise RuntimeError(
        f"Environment variable {name} is not set after waiting {timeout} seconds"
    )


async def periodic_task(stop_event: asyncio.Event, db_url: str, mariadb_url: str):
    while not stop_event.is_set():
        print("[DEBUG] Starting periodic data fetch")
        try:
            await get_rockd_data(mariadb_url, db_url)
            print("[DEBUG] Finished get_rockd_data")
            await get_macrostrat_data(mariadb_url, db_url)
            print("[DEBUG] Finished get_macrostrat_data")
        except Exception:
            print("Error in periodic_task:", flush=True)
            traceback.print_exc()

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=30)
        except asyncio.TimeoutError:
            pass


async def main():
    stop_event = asyncio.Event()
    # Fetch environment variables once at startup
    db_url = get_env_var("DATABASE_URL")
    mariadb_url = get_env_var("MARIADB_URL")

    loop = asyncio.get_running_loop()
    for sig in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(getattr(signal, sig), stop_event.set)

    await periodic_task(stop_event, db_url, mariadb_url)


if __name__ == "__main__":
    asyncio.run(main())
