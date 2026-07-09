import asyncio

from src.adapters.conad import CONAD
from src.runner import run_main

if __name__ == "__main__":
    asyncio.run(run_main("conad", CONAD))
