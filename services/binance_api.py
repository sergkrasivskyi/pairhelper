import httpx
from functools import lru_cache

BINANCE_URL = "https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"

@lru_cache(maxsize=100)  # кешування до 100 запитів
async def get_price_usdt(symbol: str) -> float:
    symbol = symbol.upper()

    async with httpx.AsyncClient(timeout=10) as client:
        url = BINANCE_URL.format(symbol=symbol)
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return float(data["price"])
        except httpx.HTTPError as e:
            raise RuntimeError(f"Помилка HTTP: {e}")
        except Exception as e:
            raise RuntimeError(f"Не вдалося отримати ціну {symbol}: {e}")

