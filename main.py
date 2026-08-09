import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
Ты — Telegram-ассистент компании forparty23.

Компания занимается техническим обеспечением мероприятий:
LED-экраны, звук, свет, сцены и технический продакшн.

Твоя задача — помогать Андрею Стехину обрабатывать входящие обращения клиентов.

Стиль общения:
- коротко;
- профессионально;
- дружелюбно;
- без канцелярита;
- не писать длинные сообщения;
- не использовать навязчивые продажи.

При новом запросе постарайся выяснить:
1. дату мероприятия;
2. площадку;
3. формат мероприятия;
4. что требуется: LED-экран, звук, свет, сцена или комплекс;
5. количество гостей, если это имеет значение.

ВАЖНО:
Не называй стоимость, если она неизвестна.
Не обещай наличие оборудования.
Не подтверждай бронирование.
Не предоставляй скидки.
Не придумывай технические характеристики.
При нестандартных технических вопросах сообщай, что задачу нужно передать техническому директору.

Сейчас система находится в тестовом режиме.
"""

def generate_answer(text):
    response = client.responses.create(
        model="gpt-5-mini",
        instructions=SYSTEM_PROMPT,
        input=text
    )

    return response.output_text


@app.route("/", methods=["GET"])
def home():
    return "ForParty23 Telegram Assistant is running", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}

    # Telegram Business messages
    message = update.get("business_message")

    # Обычные сообщения боту — удобно для тестирования
    if message is None:
        message = update.get("message")

    if not message:
        return jsonify({"ok": True})

    text = message.get("text")

    if not text:
        return jsonify({"ok": True})

    chat_id = message["chat"]["id"]
    business_connection_id = message.get("business_connection_id")

    try:
        answer = generate_answer(text)

        payload = {
            "chat_id": chat_id,
            "text": answer
        }

        if business_connection_id:
            payload["business_connection_id"] = business_connection_id

        telegram_url = (
            f"https://api.telegram.org/bot"
            f"{TELEGRAM_BOT_TOKEN}/sendMessage"
        )

        requests.post(
            telegram_url,
            json=payload,
            timeout=20
        )

    except Exception as e:
        print("ERROR:", str(e))

    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
