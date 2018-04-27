import numpy
import time
import ccxt
import subprocess
import os
import asyncio
import cachetools.func

from slackclient import SlackClient
from rsi import rsiFunc

token = os.environ.get("SLACK_API_TOKEN", "")
slack = SlackClient(token)
counter_currencies = ["BTC", "USD", "USDT"]

@cachetools.func.ttl_cache(maxsize=1000, ttl=3600)
def alert(message):
    try:
        subprocess.Popen(
            ['notify-send', '-t', '15000', 'Warning!', "\n" + message])
        subprocess.Popen(["espeak", "-v+f4", message])
    except:
        pass # notify-send and espaky might not be installed (e.g on server)

    if token:
        slack.api_call("chat.postMessage",
                       channel=os.environ["SLACK_CHANNEL"],
                       text=message)
    print(message)

async def check_rsi(symbol, timeframe, exchange):
    candles = exchange.fetch_ohlcv(symbol, timeframe)
    close = numpy.array(candles)[:, 4]
    volume = (numpy.array(candles)[:, 5])[-10:].sum() * close[-1]
    rsi = round(rsiFunc(close)[-1], 2)
    await asyncio.sleep(exchange.rateLimit / 1000)

    return {
        'oversold': rsi < (20 if timeframe == '5m' else 25),
        'overbought': rsi > (80 if timeframe == '5m' else 75),
        'symbol': symbol, 'timeframe': timeframe,
        'rsi': rsi, 'volume': volume
    }

def print_values(i):
    print('\033[31m' if i["oversold"] else '',
          i["symbol"], i["timeframe"], i["volume"],
          i["rsi"], '\033[0m')

async def check_oversold(symbol, exchange, timeframe):
    if symbol.split("/")[1] not in counter_currencies:
        return

    rsi_values = [await check_rsi(symbol, t, exchange) for t in timeframe]
    print(exchange.name)

    list(map(print_values, rsi_values))

    def rsi_alert(key):
        if sum(o.get(key) == True for o in rsi_values) > 3:
            alert(exchange.name + ": " + symbol + " " + key + " alert")

    list(map(rsi_alert, ["oversold", "overbought"]))
    print("") # delimiter

async def check(exchange, timeframe):
    while True:
        try:
            [await check_oversold(symbol, exchange, timeframe)
             for symbol in exchange.load_markets()]
        except Exception as e:
            print(e)

exchanges = [
    (ccxt.gdax(), ['5m', '15m', '1h', '6h']),
    (ccxt.binance(), ['5m', '15m', '1h', '4h'])
]

# low volume
#  (ccxt.bittrex(), ['5m', '30m', '1h', '1d']),
#  (ccxt.poloniex(), ['5m', '15m', '2h', '4h']),

tasks = [check(e,t) for e,t in exchanges]

alert("RSI Alert Bot started")
asyncio.get_event_loop().run_until_complete(asyncio.wait(tasks))
