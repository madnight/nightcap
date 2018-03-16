import numpy
import time
import ccxt
import subprocess
import os
from rsi import rsiFunc
from slackclient import SlackClient



exchange = ccxt.binance()
markets = exchange.load_markets()
slack = SlackClient(os.environ["SLACK_API_TOKEN"])


def alert(message):
    subprocess.Popen(['notify-send', '-t', '15000', 'Warning!', "\n" + message])
    subprocess.Popen(["espeak", "-v+f4", message])
    slack.api_call("chat.postMessage",
                   channel=os.environ["SLACK_CHANNEL"],
                   text=message)
    print (message)

def check_rsi(symbol, timeframe):
    candles = exchange.fetch_ohlcv (symbol, timeframe)
    close = numpy.array(candles)[:,4]
    rsi = round(rsiFunc(close)[-1], 2)
    oversold = rsi < 30
    print ('\033[31m' if oversold else '', symbol, timeframe, rsi, '\033[0m')
    time.sleep (exchange.rateLimit / 1000)
    return oversold

def check_oversold(symbol):
    oversolds = [check_rsi(symbol, t) for t in ['5m', '15m', '1h', '4h', '1d']]
    if (oversolds.count(True) > 3):
        alert(symbol + " oversold alert")
    print ("")

alert("RSI Alert Bot started")

while True:
    [check_oversold(symbol) for symbol in markets]
