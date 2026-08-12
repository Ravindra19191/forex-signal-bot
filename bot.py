import os
import requests
from telegram import Bot

# GitHub Secrets වලින් Telegram Token සහ Chat ID ලබා ගැනීම
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

bot = Bot(token=TOKEN)

# ප්‍රධාන කරන්ට් යුගල කිහිපයක් ස්කෑන් කිරීම (Free API එකක් හරහා මිල ගණන් ලබා ගැනීම)
pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

def check_markets_and_send():
    messages = []
    
    for symbol in pairs:
        try:
            # නොමිලේ ප්‍රයිස් ඩේටා ලබාගැනීම සඳහා API එකක් භාවිතය
            url = f"https://api.exchangerate-host.com/latest?base={symbol[:3]}&symbols={symbol[3:]}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if "rates" in data and symbol[3:] in data["rates"]:
                rate = data["rates"][symbol[3:]]
                
                # මෙතැනට ඔයාගේ ඉඩිකේටර් කොන්දේසි (VIDYA, Tow-Pole වැනි දේ) දාගත හැක
                # උදාහරණයක් ලෙස ප්‍රයිස් එක චෙක් කරනပုံ:
                signal_text = (
                    f"🟢 **MARKET UPDATE / SIGNAL**\n"
                    f"🔹 **Pair:** {symbol}\n"
                    f"🔹 **Current Rate:** {rate:.5f}\n"
                    f"📝 **Status:** Scanned successfully via GitHub Actions!"
                )
                messages.append(signal_text)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

    # Telegram වෙත මැසේජ් යැවීම
    if messages and CHAT_ID:
        for msg in messages:
            bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
            
if __name__ == "__main__":
    check_markets_and_send()
