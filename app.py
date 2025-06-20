from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
from bs4 import BeautifulSoup
import re
import os
import json

app = Flask(__name__)

# ✅ 替換為你自己的 LINE Token 和 Secret
LINE_CHANNEL_ACCESS_TOKEN = 'mQv7nvuVfG58XrY1UKu9wyzeIHwcH3B5QBAycTYy6QY3yxfP5roSLx+waGBS2mfyl/oQqJP1Pk21xZkxCiobAj2gMPbPDwRXCfnHp52wt6B/OG0QpdQ6cQsyleJd3XdDQ6eO/n3qCj3hOkaSM69SnQdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '05be5ec479f89f2928e95ccbfd61fb4c'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    if text in ["查價格", "價格", "椰殼價格", "煤炭價格", "溴素價格"]:
        reply = ""

        # 椰殼活性碳價格
        coconut = fetch_coconut_prices()
        if coconut:
            reply += "🌍 椰殼活性碳價格：\n"
            for region, data in coconut.items():
                arrow = "⬆️" if data["change"] > 0 else "⬇️"
                reply += f"{region}：US${data['price']} /KG  {arrow} {abs(data['change'])}%\n"
        else:
            reply += "椰殼活性碳價格 ❌ 抓取失敗\n"

        # 煤炭價格（FRED）
        coal = fetch_fred_coal_price()
        if coal:
            reply += f"\n🪨 煤炭價格（FRED）：${coal['price']} USD/ton（{coal['date']}）\n"
        else:
            reply += "\n🪨 煤炭價格（FRED）❌ 抓取失敗\n"

        # 溴素價格（卓創）
        bromine = fetch_bromine_price()
        if bromine:
            reply += f"\n🧪 溴素價格（中國）：{bromine['price']} 元/噸（{bromine['date']}）\n"
        else:
            reply += "\n🧪 溴素價格 ❌ 抓取失敗\n"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入「查價格」即可查詢椰殼活性碳、煤炭與溴素價格 📊")
        )

# === 價格抓取邏輯 ===

def fetch_coconut_prices():
    url = "https://businessanalytiq.com/procurementanalytics/index/activated-charcoal-prices/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    heading = None
    for h3 in soup.find_all("h3"):
        if "activated carbon price" in h3.text.lower():
            heading = h3
            break

    prices = {}
    if heading:
        ul = heading.find_next_sibling("ul")
        if ul:
            for li in ul.find_all("li"):
                text = li.get_text(strip=True)
                match = re.match(r"(.+):US\$(\d+\.\d+)/KG,?\s*([-+]?\d+\.?\d*)%?\s*(up|down)?", text)
                if match:
                    region = match.group(1).strip()
                    price = float(match.group(2))
                    change = float(match.group(3))
                    direction = match.group(4)
                    if direction == "down":
                        change = -abs(change)
                    prices[region] = {"price": price, "change": change}
    return prices

def fetch_fred_coal_price():
    url = "https://api.stlouisfed.org/fred/series/observations?series_id=PCU21212121&api_key=YOUR_API_KEY&file_type=json"
    # ❗ 如無 API 金鑰，可考慮使用 HTML fallback
    try:
        fallback_url = "https://fred.stlouisfed.org/series/PCU21212121"
        res = requests.get(fallback_url)
        soup = BeautifulSoup(res.text, "html.parser")
        script = soup.find("script", string=re.compile("pageData"))
        if not script: return None

        json_text = re.search(r'var pageData = ({.*?});', script.string, re.DOTALL)
        if not json_text: return None

        data = json.loads(json_text.group(1))
        latest = data["seriestree"]["series"][0]["data"][-1]
        return {"date": latest["date"], "price": latest["value"]}
    except Exception as e:
        print("FRED Coal Error:", e)
        return None

def fetch_bromine_price():
    url = "https://pdata.100ppi.com/?f=basket&dir=hghy&id=643"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers)
        json_text = re.search(r"var data=(\[{.*?\}]);", res.text)
        if not json_text:
            return None
        data = json.loads(json_text.group(1))
        latest = data[-1]  # 取最後一筆最新價格
        return {"date": latest["date"], "price": latest["value"]}
    except Exception as e:
        print("Bromine Error:", e)
        return None

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
