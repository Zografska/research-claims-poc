import asyncio

from src.adapters.eurospin import EUROSPIN
from src.runner import run_main

if __name__ == "__main__":
    asyncio.run(run_main("eurospin", EUROSPIN))
