import asyncio

from src.adapters.conad import CONAD
from src.stages.link_collector import collect_links
from src.utils.logger import setup_logger
from src.utils.parser import get_conad_parser


async def main():
    parser = get_conad_parser()
    args = parser.parse_args()

    setup_logger()

    if args.stage == 1:
        await collect_links(CONAD, max_pages=args.pages)


if __name__ == "__main__":
    asyncio.run(main())
