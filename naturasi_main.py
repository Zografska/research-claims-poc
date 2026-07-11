import asyncio

from src.adapters.naturasi import NATURASI
from src.runner import run_main

if __name__ == "__main__":
    asyncio.run(run_main("naturasi", NATURASI))
