import os
import json
import time
import uuid
import logging
import threading
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "").strip()
# Separate business chats by commas. Empty = no Business auto-replies.
BUSINESS_ALLOWED_CHAT_IDS = {
    value.strip() for value in os.environ.get("BUSINESS_ALLOWED_CHAT_IDS", "").split(",")
    if value.strip()
}
# For a safer launch, direct messages to the bot are restricted to your own ID.
BOT_ALLOWED_CHAT_IDS = {
    value.strip() for value in os.environ.get("BOT_ALLOWED_CHAT_IDS", "").split(",")
    if value.strip()
}
WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()

client = OpenAI(api_key=OPENAI_API_KEY, timeout=25.0)
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"

# Pending drafts live in memory. They disappear if Railway restarts.
pending = {}
pending_lock = threading.Lock()
DRAFT_TTL_SECONDS = 24 * 3600

SYSTEM_PROMPT = """
Ты — AI-менеджер ForParty23 (техническое обеспечение мероприятий в Краснодаре и крае).
Услуги: аренда LED-экранов, LED-фотозон, звука, света, сцены, технический продакшн.
Общайся коротко, дружелюбно и по делу, не больше 2-4 предложений за раз.
При необходимости уточняй дату, площадку, формат, задачу и число гостей.
Не придумывай цены, наличие, свободные даты, скидки, характеристики и сроки.
Не подтверждай бронирования, договоры, оплату и обязательства компании.
Если вопрос о цене, смете, скидке, наличии, бронировании, договоре, оплате,
сложной технической задаче или жалобе — requires_approval=true.
Даже когда требуется согласование, подготовь полезный, осторожный черновик.
Ответь ТОЛЬКО JSON-объектом с полями requires_approval (boolean) и reply (string).
Никакого markdown вокруг JSON.
"""

# Extra fail-safe: even if AI misclassifies a high-stakes question,
# don't automatically send a business commitment.
RISK_WORDS = (
    "цен", "стоим", "сколько", "руб", "бюджет", "смет", "скид", "дешев",
    "налич", "свобод", "брони", "резерв", "договор", "оплат", "предоплат",
    "счет", "счёт", "гарант", "срок", "техзадан", "тз", "райдер",
    "жалоб", "претензи", "верните", "возврат", "обязательств",
)


def telegram(method, data):
    response = requests.post(TELEGRAM_URL + method, json=data, timeout=15)
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API failed: {result.get('description', 'unknown error')}")
    return result


def classify_and_draft(message):
    result = client.responses.create(
        model="gpt-5-mini",
        instructions=SYSTEM_PROMPT,
        input=message,
        max_output_tokens=450,
    )
    raw = result.output_text.strip()
    data = json.loads(raw)
    reply = str(data["reply"]).strip()[:3500]
    if not reply:
        raise ValueError("Empty AI response")
    risky = bool(data.get("requires_approval")) or any(
        word in message.casefold() for word in RISK_WORDS
    )
    return risky, reply


def notify_for_approval(chat_id, business_connection_id, original, draft):
    if not ADMIN_CHAT_ID:
        logging.warning("ADMIN_CHAT_ID absent; sensitive reply was not sent")
        return
    draft_id = uuid.uuid4().hex[:20]
    with pending_lock:
        now = time.time()
        for key, entry in list(pending.items()):
            if now - entry["created"] > DRAFT_TTL_SECONDS:
                del pending[key]
        pending[draft_id] = {
            "chat_id": chat_id,
            "business_connection_id": business_connection_id,
            "reply": draft,
            "created": now,
        }
    message = (
        f"⏳ Согласование ответа ForParty23\n"
        f"Чат: {chat_id}\n"
        f"Клиент: {original[:900]}\n\n"
        f"Черновик:\n{draft[:2400]}"
    )
    try:
        telegram("sendMessage", {
            "chat_id": ADMIN_CHAT_ID,
            "text": message,
            "reply_markup": {"inline_keyboard": [[
                {"text": "✅ Отправить", "callback_data": f"ok:{draft_id}"},
                {"text": "❌ Отклонить", "callback_data": f"no:{draft_id}"},
            ]]},
        })
    except Exception:
        with pending_lock:
            pending.pop(draft_id, None)
        raise


def handle_approval(callback):
    callback_id = callback.get("id")
    origin = callback.get("message") or {}
    admin_user_id = str((callback.get("from") or {}).get("id", ""))
    admin_chat_id = str((origin.get("chat") or {}).get("id", ""))
    # ADMIN_CHAT_ID is a private chat ID, normally equal to user ID.
    if not ADMIN_CHAT_ID or admin_chat_id != ADMIN_CHAT_ID or admin_user_id != ADMIN_CHAT_ID:
        if callback_id:
            telegram("answerCallbackQuery", {"callback_query_id": callback_id, "text": "Нет доступа"})
        return
    action, _, draft_id = (callback.get("data") or "").partition(":")
    if action not in ("ok", "no"):
        return
    with pending_lock:
        item = pending.pop(draft_id, None)
    if not item or time.time() - item["created"] > DRAFT_TTL_SECONDS:
        telegram("answerCallbackQuery", {"callback_query_id": callback_id, "text": "Черновик устарел"})
        return
    if action == "ok":
        payload = {"chat_id": item["chat_id"], "text": item["reply"]}
        if item["business_connection_id"]:
            payload["business_connection_id"] = item["business_connection_id"]
        try:
            telegram("sendMessage", payload)
            text = "Отправлено клиенту"
        except Exception:
            logging.exception("Approved draft send failed")
            text = "Ошибка отправки. Посмотрите логи."
    else:
        text = "Ответ отклонён"
    telegram("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})
    telegram("editMessageReplyMarkup", {
        "chat_id": ADMIN_CHAT_ID,
        "message_id": origin["message_id"],
        "reply_markup": {"inline_keyboard": []},
    })


@app.route("/", methods=["GET"])
def home():
    return "ForParty23 Telegram Assistant is running", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    if WEBHOOK_SECRET and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return jsonify({"ok": False}), 403
    update = request.get_json(silent=True) or {}
    try:
        if update.get("callback_query"):
            handle_approval(update["callback_query"])
            return jsonify({"ok": True})

        business = update.get("business_message") is not None
        message = update.get("business_message") if business else update.get("message")
        if not message or not message.get("text"):
            return jsonify({"ok": True})
        chat = message.get("chat", {})
        if chat.get("type") != "private":
            return jsonify({"ok": True})
        chat_id = str(chat.get("id", ""))
        if chat_id == ADMIN_CHAT_ID:
            return jsonify({"ok": True})
        if (message.get("from") or {}).get("is_bot"):
            return jsonify({"ok": True})
        if business:
            if chat_id not in BUSINESS_ALLOWED_CHAT_IDS:
                return jsonify({"ok": True})
        elif not BOT_ALLOWED_CHAT_IDS or chat_id not in BOT_ALLOWED_CHAT_IDS:
            return jsonify({"ok": True})

        business_id = message.get("business_connection_id") if business else None
        needs_approval, draft = classify_and_draft(message["text"])
        if needs_approval:
            notify_for_approval(chat_id, business_id, message["text"], draft)
        else:
            payload = {"chat_id": chat_id, "text": draft}
            if business_id:
                payload["business_connection_id"] = business_id
            telegram("sendMessage", payload)
    except Exception:
        logging.exception("Webhook error")
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
