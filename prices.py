from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import threading

from prices import fetch_coconut_prices, fetch_fred_from_ycharts, fetch_bromine_details, fetch_cnyes_energy2_close_price

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

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
        # 快速回覆
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="📡 查詢中，請稍候...")
        )
        # 背景處理並推播完整資訊
        user_id = event.source.user_id
        print("[Debug] 查詢啟動, user_id =", user_id)
        threading.Thread(target=send_price_result, args=(user_id,)).start()
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入「查價格」即可查詢椰殼活性碳、煤炭與溴素價格 📊")
        )

def send_price_result(user_id):
    try:
        reply = ""

        coconut = fetch_coconut_prices()
        if coconut:
            reply += "🥥 椰殼活性碳價格：\n"
            for region, data in coconut.items():
                arrow = "⬆️" if data["change"] > 0 else "⬇️"
                date = f"（{data['date']}）" if data['date'] else ""
                reply += f"{region}：US${data['price']} /KG  {arrow} {abs(data['change'])}% {date}\n"
        else:
            reply += "❌ 椰殼活性碳抓取失敗\n"

        latest_date, latest_val, change = fetch_fred_from_ycharts()
        reply += "\n🪨 煤質活性碳價格：\n"
        if latest_val:
            if change:
                arrow = "⬆️" if "-" not in change else "⬇️"
                reply += f"FRED：{latest_val}（{latest_date}，月變動 {arrow} {change}）\n"
            else:
                reply += f"FRED：{latest_val}（{latest_date}）\n"
        else:
            reply += "FRED ❌ 抓取失敗\n"

        coal_keywords = [["紐約煤西北歐"], ["倫敦煤澳洲"], ["大連焦煤"]]
        for kw in coal_keywords:
            reply += fetch_cnyes_energy2_close_price(kw) + "\n"

        bromine = fetch_bromine_details()
        reply += "\n🧪 溴素最新價格：\n"
        if bromine:
            reply += bromine + "\n"
        else:
            reply += "溴素價格 ❌ 抓取失敗\n"

        print("[Debug] 準備推播訊息給 user_id:", user_id)
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=reply.strip())
        )
        print("[Debug] 推播完成")

    except Exception as e:
        print("[錯誤] 背景推播失敗：", e)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
