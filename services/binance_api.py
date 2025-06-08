import requests

def get_price_usdt(symbol):
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}USDT'
    response = requests.get(url)
    data = response.json()
    return float(data['price'])
