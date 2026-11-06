import ccxt
import pandas as pd
import time
import os
from datetime import datetime

# ====== SETTINGS ======
SYMBOL = "BTC/USDT"
SHORT_WINDOW = 9
LONG_WINDOW = 21
TRADE_PERCENT = 0.95          # Use 95% of available balance
CHECK_INTERVAL = 60           # Check every 60 seconds
# ======================

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_SECRET_KEY")

if not api_key or not api_secret:
    print("ERROR: API keys not found. Add them as environment variables.")
    exit()

exchange = ccxt.binance({
    "apiKey": api_key,
    "secret": api_secret,
    "enableRateLimit": True,
    "options": {"defaultType": "spot"},
})

# Point to Binance Spot Testnet
exchange.set_sandbox_mode(True)

def get_ohlcv():
    bars = exchange.fetch_ohlcv(SYMBOL, timeframe="1m", limit=LONG_WINDOW + 5)
    df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
    return df

def get_balance():
    balance = exchange.fetch_balance()
    usdt = balance["USDT"]["free"]
    btc = balance["BTC"]["free"]
    return usdt, btc

def place_buy(usdt_amount):
    try:
        order = exchange.create_market_buy_order(SYMBOL, None, params={"quoteOrderQty": usdt_amount})
        print(f"{datetime.now()} - BUY order placed: {order['id']}")
        return True
    except Exception as e:
        print(f"{datetime.now()} - Buy error: {e}")
        return False

def place_sell(btc_amount):
    try:
        order = exchange.create_market_sell_order(SYMBOL, btc_amount)
        print(f"{datetime.now()} - SELL order placed: {order['id']}")
        return True
    except Exception as e:
        print(f"{datetime.now()} - Sell error: {e}")
        return False

def main():
    print(f"{datetime.now()} - Bot started on Binance Testnet")
    print(f"Strategy: {SHORT_WINDOW}/{LONG_WINDOW} SMA crossover on {SYMBOL}")

    last_signal = None

    while True:
        try:
            df = get_ohlcv()
            df["sma_short"] = df["close"].rolling(window=SHORT_WINDOW).mean()
            df["sma_long"] = df["close"].rolling(window=LONG_WINDOW).mean()

            current_short = df["sma_short"].iloc[-1]
            current_long = df["sma_long"].iloc[-1]
            prev_short = df["sma_short"].iloc[-2]
            prev_long = df["sma_long"].iloc[-2]

            usdt, btc = get_balance()
            print(f"{datetime.now()} - USDT: {usdt:.2f} | BTC: {btc:.6f} | SMA9: {current_short:.2f} | SMA21: {current_long:.2f}")

            # Buy signal: short crosses above long
            if prev_short <= prev_long and current_short > current_long and last_signal != "buy":
                if usdt > 5:
                    amount = usdt * TRADE_PERCENT
                    if place_buy(amount):
                        last_signal = "buy"
                else:
                    print("Not enough USDT to buy")

            # Sell signal: short crosses below long
            elif prev_short >= prev_long and current_short < current_long and last_signal != "sell":
                if btc > 0.0001:
                    if place_sell(btc):
                        last_signal = "sell"
                else:
                    print("Not enough BTC to sell")

            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"{datetime.now()} - Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
