from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

# ✅ 替換成你自己的 channel access token / secret
LINE_CHANNEL_ACCESS_TOKEN = '你的 access token'
LINE_CHANNEL_SECRET = '你的 secret'

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
    user_msg = event.message.text.strip()

    if user_msg == "查價格":
        reply = (
            "🌍 測試價格列表：\n\n"
            "✅ 椰殼活性碳：US$2.10/KG（⬇️ 0.5%）\n"
            "✅ 煤炭價格：US$63.52/ton（2025-06-17）\n"
            "✅ 溴素價格：25,100 元/噸（2025-06-19）"
        )
    else:
        reply = "請輸入「查價格」即可獲取測試價格 📊"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
