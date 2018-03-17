import numpy
import time
import ccxt
import subprocess
import os
import asyncio

from slackclient import SlackClient
from rsi import rsiFunc

slack = SlackClient(os.environ["SLACK_API_TOKEN"])

counter_currencies = ["BTC", "USD", "USDT"]

def alert(message):
    try:
        subprocess.Popen(
            ['notify-send', '-t', '15000', 'Warning!', "\n" + message])
        subprocess.Popen(["espeak", "-v+f4", message])
    except:
        pass # notify-send and espaky might not be installed (e.g on server)
    slack.api_call("chat.postMessage",
                   channel=os.environ["SLACK_CHANNEL"],
                   text=message)
    print(message)

async def check_rsi(symbol, timeframe, exchange):
    candles = exchange.fetch_ohlcv(symbol, timeframe)
    close = numpy.array(candles)[:, 4]
    volume = (numpy.array(candles)[:, 5])[-10:].sum()
    rsi = round(rsiFunc(close)[-1], 2)
    oversold = rsi < (25 if timeframe == '5m' else 28)
    await asyncio.sleep(exchange.rateLimit / 1000)
    return {
        'oversold': oversold, 'symbol': symbol,
        'timeframe': timeframe, 'rsi': rsi,
        'volume': volume
    }

def print_values(i):
    print('\033[31m' if i["oversold"] else '',
          i["symbol"], i["timeframe"], i["volume"],
          i["rsi"], '\033[0m')

async def check_oversold(symbol, exchange, timeframe):
    if symbol.split("/")[1] not in counter_currencies:
        return
    oversolds = [await check_rsi(symbol, t, exchange) for t in timeframe]
    print(exchange.name)
    list(map(print_values, oversolds))
    if sum(o.get('oversold') == True for o in oversolds) > 3:
        alert(exchange.name + ": " + symbol + " oversold alert")
    print("")


async def check(exchange, timeframe):
    while True:
        try:
            [await check_oversold(symbol, exchange, timeframe)
             for symbol in exchange.load_markets()]
        except Exception as e:
            print(e)

exchanges = [
    (ccxt.gdax(), ['5m', '15m', '1h', '6h']),
    (ccxt.bittrex(), ['5m', '30m', '1h', '1d']),
    (ccxt.poloniex(), ['5m', '15m', '2h', '4h']),
    (ccxt.binance(), ['5m', '15m', '1h', '4h'])
]
tasks = [check(e,t) for e,t in exchanges]

alert("RSI Alert Bot started")
asyncio.get_event_loop().run_until_complete(asyncio.wait(tasks))
