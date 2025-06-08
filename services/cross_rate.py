from services.binance_api import get_price_usdt

async def get_cross_rate(token_a: str, token_b: str) -> float:
    price_a = await get_price_usdt(token_a)
    price_b = await get_price_usdt(token_b)

    if price_b == 0:
        raise ValueError("Ціна токена B не може бути 0")

    return price_a / price_b
