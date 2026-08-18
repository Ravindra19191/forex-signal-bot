import os
import requests
import pandas as pd
import numpy as np

# 1. Telegram Configurations (GitHub Secrets වලින් ටෝකන් ලබාගනී)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

# 2. නිදහස් මාකට් ඩේටා ලබාගැනීම (Yahoo Finance හරහා EURUSD 15m කෑන්ඩල්ස්)
def get_market_data():
    try:
        # EURUSD පයා එකේ මෑතකදී සිදුවූ මිල ගණන් ලබාගැනීම (15m Timeframe)
        url = "https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?interval=15m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        data = response.json()
        
        result = data['chart']['result'][0]
        closes = result['indicators']['quote'][0]['close']
        volumes = result['indicators']['quote'][0]['volume']
        
        # None අගයන් මගහරවා ගැනීම
        df = pd.DataFrame({'close': closes, 'volume': volumes}).dropna()
        return df
    except Exception as e:
        print(f"Data fetch error: {e}")
        return None

# 3. ඉඩිකේටර් ලොජික් කැල්කියුලේෂන්
def calculate_indicators(df):
    close = df['close']
    volume = df['volume']
    
    # --- A. VIDYA Calculation ---
    window = 9
    sc = 0.2
    change = close.diff()
    up = np.where(change > 0, change, 0.0)
    down = np.where(change < 0, abs(change), 0.0)
    
    sum_up = pd.Series(up).rolling(window=window).sum()
    sum_down = pd.Series(down).rolling(window=window).sum()
    cmo = abs((sum_up - sum_down) / (sum_up + sum_down)).fillna(0)
    
    vidya = [close.iloc[0]]
    for i in range(1, len(close)):
        alpha = sc * cmo.iloc[i]
        v_curr = (alpha * close.iloc[i]) + ((1 - alpha) * vidya[-1])
        vidya.append(v_curr)
    df['vidya'] = vidya
    
    # --- B. Two-Pole Trend Filter (EMA Crossover මත පදනම්ව) ---
    df['fast_ma'] = close.ewm(span=5, adjust=False).mean()
    df['slow_ma'] = close.ewm(span=13, adjust=False).mean()
    
    # --- C. Delta Volume (Volume Direction) ---
    df['price_change'] = close.diff()
    df['buy_vol'] = np.where(df['price_change'] >= 0, volume, 0)
    df['sell_vol'] = np.where(df['price_change'] < 0, volume, 0)
    df['delta'] = df['buy_vol'].rolling(3).sum() - df['sell_vol'].rolling(3).sum()
    
    # --- D. RSI (35 - 65 Range) ---
    delta_rsi = close.diff()
    gain = (delta_rsi.where(delta_rsi > 0, 0)).rolling(window=14).mean()
    loss = (-delta_rsi.where(delta_rsi < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df.iloc[-1] # නවතම කැල්කියුලේටඩ් පේළිය පමණක් ලබා දීම

# 4. සිග්නල් පරීක්ෂාව සහ යැවීම
def run_bot():
    df = get_market_data()
    if df is None or len(df) < 20:
        print("Not enough data")
        return
        
    latest = calculate_indicators(df)
    
    c_price = latest['close']
    vidya_val = latest['vidya']
    fast_ma = latest['fast_ma']
    slow_ma = latest['slow_ma']
    rsi_val = latest['rsi']
    delta_val = latest['delta']
    
    # කොන්දේසි පරීක්ෂා කිරීම (Confluence Strategy)
    # Buy Condition: Price > VIDYA, Fast MA > Slow MA, RSI 35 සහ 65 අතර, Delta Positive
    is_buy = (c_price > vidya_val) and (fast_ma > slow_ma) and (35 <= rsi_val <= 65) and (delta_val > 0)
    
    # Sell Condition: Price < VIDYA, Fast MA < Slow MA, RSI 35 සහ 65 අතර, Delta Negative
    is_sell = (c_price < vidya_val) and (fast_ma < slow_ma) and (35 <= rsi_val <= 65) and (delta_val < 0)
    
    if is_buy:
        msg = (
            "🟢 *EURUSD BUY SIGNAL DETECTED* 🟢\n\n"
            f"• *Price:* {c_price:.5f}\n"
            f"• *VIDYA:* {vidya_val:.5f}\n"
            f"• *RSI:* {rsi_val:.2f} (Neutral Zone 35-65)\n"
            f"• *Delta Volume:* Bullish Pressure\n\n"
            "⚠️ *Account Note:* Use 0.01 Micro Lot (0.62$ Balance Manager)"
        )
        send_telegram_message(msg)
    elif is_sell:
        msg = (
            "🔴 *EURUSD SELL SIGNAL DETECTED* 🔴\n\n"
            f"• *Price:* {c_price:.5f}\n"
            f"• *VIDYA:* {vidya_val:.5f}\n"
            f"• *RSI:* {rsi_val:.2f} (Neutral Zone 35-65)\n"
            f"• *Delta Volume:* Bearish Pressure\n\n"
            "⚠️ *Account Note:* Use 0.01 Micro Lot (0.62$ Balance Manager)"
        )
        send_telegram_message(msg)
    else:
        print(f"No strict signal. Current RSI: {rsi_val:.2f}, Price: {c_price:.5f}")

if __name__ == "__main__":
    run_bot()
