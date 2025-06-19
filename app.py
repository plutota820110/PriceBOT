from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)

# 替換成你的 LINE Channel Access Token 和 Secret
LINE_CHANNEL_ACCESS_TOKEN = 'mQv7nvuVfG58XrY1UKu9wyzeIHwcH3B5QBAycTYy6QY3yxfP5roSLx+waGBS2mfyl/oQqJP1Pk21xZkxCiobAj2gMPbPDwRXCfnHp52wt6B/OG0QpdQ6cQsyleJd3XdDQ6eO/n3qCj3hOkaSM69SnQdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '05be5ec479f89f2928e95ccbfd61fb4c'

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 主程式路由
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 當收到訊息時的處理邏輯
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    if text in ["查價格", "價格", "椰殼價格"]:
        prices = fetch_prices()
        reply = "🌍 椰殼活性碳最新價格：\n"
        for region, data in prices.items():
            arrow = "⬆️" if data["change"] > 0 else "⬇️"
            reply += f"{region}：US${data['price']} /KG  {arrow} {abs(data['change'])}%\n"
    else:
        reply = "請輸入「查價格」即可查詢椰殼活性碳價格 📊"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# 抓取價格的函數（你之前的邏輯）
def fetch_prices():
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

if __name__ == "__main__":
    app.run(debug=True)
