import httpx
import asyncio
from functools import lru_cache

# ──────────────────────────────────────────────────────────────
# Асинхронно отримуємо ціну токена в USDT
# ──────────────────────────────────────────────────────────────
async def _get_price_usdt(symbol: str, client: httpx.AsyncClient) -> float:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}USDT"
    resp = await client.get(url, timeout=5)
    resp.raise_for_status()
    return float(resp.json()["price"])

# ──────────────────────────────────────────────────────────────
# Публічна функція: кроскурс token_a / token_b
# ──────────────────────────────────────────────────────────────
async def get_cross_rate(token_a: str, token_b: str) -> float:
    """
    Повертає cross-rate token_a / token_b, запитуючи ціни обох токенів до USDT.
    Використовує один спільний AsyncClient, тому **НЕ** виникає повторного await.
    """
    async with httpx.AsyncClient() as client:
        price_a, price_b = await asyncio.gather(
            _get_price_usdt(token_a, client),
            _get_price_usdt(token_b, client)
        )
    return price_a / price_b
