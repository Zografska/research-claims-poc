import asyncio

from src.adapters.carrefour import CARREFOUR
from src.runner import run_main

if __name__ == "__main__":
    asyncio.run(run_main("carrefour", CARREFOUR))
