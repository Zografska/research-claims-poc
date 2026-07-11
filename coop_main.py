import asyncio

from src.adapters.coop import COOP
from src.runner import run_main

if __name__ == "__main__":
    asyncio.run(run_main("coop", COOP))
