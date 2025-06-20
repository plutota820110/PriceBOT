from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from prices import (
    fetch_coconut_prices,
    fetch_fred_from_ycharts,
    fetch_bromine_details,
    fetch_cnyes_energy2_close_price
)

import os

app = Flask(__name__)

# ✅ 替換為你自己的 LINE TOKEN 和 SECRET
LINE_CHANNEL_ACCESS_TOKEN = os.getenv(mQv7nvuVfG58XrY1UKu9wyzeIHwcH3B5QBAycTYy6QY3yxfP5roSLx+waGBS2mfyl/oQqJP1Pk21xZkxCiobAj2gMPbPDwRXCfnHp52wt6B/OG0QpdQ6cQsyleJd3XdDQ6eO/n3qCj3hOkaSM69SnQdB04t89/1O/w1cDnyilFU=)
LINE_CHANNEL_SECRET = os.getenv(05be5ec479f89f2928e95ccbfd61fb4c)

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
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
            reply += "\U0001F965 椰殼活性碳價格：\n"
            for region, data in coconut.items():
                arrow = "⬆️" if data["change"] > 0 else "⬇️"
                date = f"（{data['date']}）" if data['date'] else ""
                reply += f"{region}：US${data['price']} /KG  {arrow} {abs(data['change'])}% {date}\n"
        else:
            reply += "椰殼活性碳價格 ❌ 抓取失敗\n"

        # 煤質活性碳（FRED）
        latest_date, latest_val, change = fetch_fred_from_ycharts()
        reply += "\n\U0001FAA8 煤質活性碳價格：\n"
        if latest_val:
            if change:
                arrow = "⬆️" if "-" not in change else "⬇️"
                reply += f"FRED：{latest_val}（{latest_date}，月變動 {arrow} {change}）\n"
            else:
                reply += f"FRED：{latest_val}（{latest_date}）\n"
        else:
            reply += "FRED ❌ 抓取失敗\n"

        # 煤期貨價格（CNYES）
        coal_keywords = [
            ["紐約煤西北歐"],
            ["倫敦煤澳洲"],
            ["大連焦煤"]
        ]
        for kw in coal_keywords:
            result = fetch_cnyes_energy2_close_price(kw)
            reply += result + "\n"

        # 溴素
        bromine = fetch_bromine_details()
        reply += "\n\U0001F9EA 溴素最新價格：\n"
        if bromine:
            reply += bromine + "\n"
        else:
            reply += "溴素價格 ❌ 抓取失敗\n"

        # 傳送 LINE 回覆
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply.strip())
        )

    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入「查價格」即可查詢椰殼活性碳、煤炭與溴素價格 📊")
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
