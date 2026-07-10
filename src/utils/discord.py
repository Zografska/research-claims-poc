import logging
import os

import httpx

LEVEL_COLORS = {
    "start": 0x3B82F6,
    "checkpoint": 0x22D3EE,
    "success": 0x22C55E,
    "warning": 0xF59E0B,
    "error": 0xEF4444,
}


async def notify_discord(message: str, level: str | None = None) -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logging.debug("DISCORD_WEBHOOK_URL not set, skipping notification")
        return

    color = LEVEL_COLORS.get(level)
    payload = {"embeds": [{"description": message, "color": color}]} if color is not None else {"content": message}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(webhook_url, json=payload)
            r.raise_for_status()
    except Exception as e:
        logging.warning(f"Discord notification failed: {e}")
