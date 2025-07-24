# src/macrostrat.py
import asyncio


async def run_task():
    print("Running macrostrat task...")
    # Your task code here
    await asyncio.sleep(0.1)  # simulate async work
    print("macrostrat task completed.")
