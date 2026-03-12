import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Храним ответы только во время прохождения теста
sessions = {}

START_TEXT = (
    "Привет! Это тест на определение типажа внешности.\n\n"
    "Нажми /start, чтобы начать."
)

# =========================
# 1) ЗДЕСЬ БУДУТ ВОПРОСЫ
# =========================
# Формат:
# "q1": {
#     "text": "Текст вопроса",
#     "options": {
#         "Текст кнопки 1": "q2",
#         "Текст кнопки 2": "q3"
#     }
# }
#
# next может вести:
# - на следующий вопрос: "q2", "q3" и т.д.
# - на результат: "result_1", "result_2" и т.д.

QUESTIONS = {
    "q1": {
        "text": "1) Вставь сюда первый вопрос",
        "options": {
            "Вариант 1": "q2",
            "Вариант 2": "q3"
        }
    },
    "q2": {
        "text": "2) Вставь сюда второй вопрос",
        "options": {
            "Вариант 1": "q4",
            "Вариант 2": "q5"
        }
    },
    "q3": {
        "text": "3) Вставь сюда третий вопрос",
        "options": {
            "Вариант 1": "q5",
            "Вариант 2": "q6"
        }
    },
    "q4": {
        "text": "4) Вставь сюда четвертый вопрос",
        "options": {
            "Вариант 1": "q7",
            "Вариант 2": "result_1"
        }
    },
    "q5": {
        "text": "5) Вставь сюда пятый вопрос",
        "options": {
            "Вариант 1": "q7",
            "Вариант 2": "q8"
        }
    },
    "q6": {
        "text": "6) Вставь сюда шестой вопрос",
        "options": {
            "Вариант 1": "q8",
            "Вариант 2": "result_2"
        }
    },
    "q7": {
        "text": "7) Вставь сюда седьмой вопрос",
        "options": {
            "Вариант 1": "q9",
            "Вариант 2": "result_3"
        }
    },
    "q8": {
        "text": "8) Вставь сюда восьмой вопрос",
        "options": {
            "Вариант 1": "q9",
            "Вариант 2": "result_4"
        }
    },
    "q9": {
        "text": "9) Вставь сюда девятый вопрос",
        "options": {
            "Вариант 1": "result_5",
            "Вариант 2": "result_6"
        }
    },
}

# =========================
# 2) ЗДЕСЬ БУДУТ 12 ИТОГОВ
# =========================
# У каждого результата:
# - title = название типажа
# - url = ссылка на сайт

RESULTS = {
    "result_1": {"title": "Типаж 1", "url": "https://example.com/1"},
    "result_2": {"title": "Типаж 2", "url": "https://example.com/2"},
    "result_3": {"title": "Типаж 3", "url": "https://example.com/3"},
    "result_4": {"title": "Типаж 4", "url": "https://example.com/4"},
    "result_5": {"title": "Типаж 5", "url": "https://example.com/5"},
    "result_6": {"title": "Типаж 6", "url": "https://example.com/6"},
    "result_7": {"title": "Типаж 7", "url": "https://example.com/7"},
    "result_8": {"title": "Типаж 8", "url": "https://example.com/8"},
    "result_9": {"title": "Типаж 9", "url": "https://example.com/9"},
    "result_10": {"title": "Типаж 10", "url": "https://example.com/10"},
    "result_11": {"title": "Типаж 11", "url": "https://example.com/11"},
    "result_12": {"title": "Типаж 12", "url": "https://example.com/12"},
}


def telegram_request(method: str, payload: dict):
    if not BOT_TOKEN:
        app.logger.error("BOT_TOKEN не задан")
        return None

    try:
        response = requests.post(
            f"{API_URL}/{method}",
            json=payload,
            timeout=20
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        app.logger.exception(f"Ошибка запроса в Telegram API: {e}")
        return None


def build_keyboard(options):
    rows = []
    current_row = []

    for option in options:
        current_row.append({"text": option})
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    rows.append([{"text": "Начать заново"}])

    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "one_time_keyboard": True
    }


def send_message(chat_id, text, keyboard=None, remove_keyboard=False):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if remove_keyboard:
        payload["reply_markup"] = {"remove_keyboard": True}
    elif keyboard:
        payload["reply_markup"] = keyboard

    telegram_request("sendMessage", payload)


def ask_question(chat_id, user_id):
    session = sessions.get(user_id)
    if not session:
        start_test(chat_id, user_id)
        return

    step = session["step"]
    question = QUESTIONS[step]
    keyboard = build_keyboard(list(question["options"].keys()))
    send_message(chat_id, question["text"], keyboard=keyboard)


def start_test(chat_id, user_id):
    sessions[user_id] = {
        "step": "q1",
        "answers": {}
    }
    ask_question(chat_id, user_id)


def finish_test(chat_id, user_id, result_id):
    result = RESULTS.get(result_id)

    if not result:
        send_message(
            chat_id,
            "Произошла ошибка: результат не найден. Напиши /start, чтобы начать заново.",
            remove_keyboard=True
        )
        sessions.pop(user_id, None)
        return

    text = (
        f"Ваш типаж: {result['title']}\n\n"
        f"Подробнее: {result['url']}\n\n"
        f"Чтобы пройти тест заново, нажмите /start"
    )

    send_message(chat_id, text, remove_keyboard=True)
    sessions.pop(user_id, None)


def process_text(chat_id, user_id, text):
    text = (text or "").strip()

    if text in ["/start", "/restart", "Начать заново"]:
        start_test(chat_id, user_id)
        return

    if user_id not in sessions:
        send_message(chat_id, START_TEXT, remove_keyboard=True)
        return

    step = sessions[user_id]["step"]
    question = QUESTIONS.get(step)

    if not question:
        send_message(chat_id, "Ошибка сценария. Нажми /start для нового прохождения.")
        sessions.pop(user_id, None)
        return

    options = question["options"]

    if text not in options:
        send_message(chat_id, "Пожалуйста, выбери один из вариантов кнопкой ниже.")
        ask_question(chat_id, user_id)
        return

    sessions[user_id]["answers"][step] = text
    next_step = options[text]

    if next_step.startswith("result_"):
        finish_test(chat_id, user_id, next_step)
        return

    if next_step not in QUESTIONS:
        send_message(chat_id, "Ошибка сценария. Нажми /start для нового прохождения.")
        sessions.pop(user_id, None)
        return

    sessions[user_id]["step"] = next_step
    ask_question(chat_id, user_id)


@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200


@app.route("/set-webhook", methods=["GET"])
def set_webhook():
    if not BOT_TOKEN:
        return jsonify({"ok": False, "error": "BOT_TOKEN is not set"}), 500

    base_url = request.url_root.rstrip("/")
    webhook_url = f"{base_url}/webhook/{BOT_TOKEN}"

    response = telegram_request("setWebhook", {"url": webhook_url})

    return jsonify({
        "ok": True,
        "webhook_url": webhook_url,
        "telegram_response": response
    }), 200


@app.route("/webhook/<secret>", methods=["POST"])
def webhook(secret):
    if secret != BOT_TOKEN:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    update = request.get_json(silent=True) or {}

    message = update.get("message", {})
    chat = message.get("chat", {})
    user = message.get("from", {})

    chat_id = chat.get("id")
    user_id = user.get("id")
    text = message.get("text", "")

    if chat_id and user_id:
        process_text(chat_id, str(user_id), text)

    return jsonify({"ok": True}), 200
