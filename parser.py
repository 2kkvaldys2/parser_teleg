from telethon import TelegramClient, events
import json
import os
from dotenv import load_dotenv

# load dotenv
load_dotenv()

# Данні API
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

# Назва сесії
session_name = "telegram_parser_active"

# Файл для останніх повідомлень
LAST_MESSAGES_FILE = "last_messages.json"

# ID каналу-приймача (закритий канал)
DEST_CHANNEL_ID = -1002403468473

# Мапа джерел → відповідні гілки (topic_id)
channel_mapping = {
    os.getenv("CH_FIRST"): int(os.getenv("FORK_FIRST")),  
    os.getenv("CH_SECOND"): int(os.getenv("FORK_SECOND")),
    os.getenv("CH_THIRD"): int(os.getenv("FORK_THIRD")),
    os.getenv("CH_FOURTH"): int(os.getenv("FORK_THIRD")),
}

# Завантаження ID останніх повідомлень
if os.path.exists(LAST_MESSAGES_FILE):
    with open(LAST_MESSAGES_FILE, "r") as f:
        last_messages = json.load(f)
else:
    last_messages = {}

# Зберігання ID повідомлення
def save_last_message(chat_id, message_id):
    last_messages[str(chat_id)] = message_id
    with open(LAST_MESSAGES_FILE, "w") as f:
        json.dump(last_messages, f)

# Створюємо клієнт
client = TelegramClient(session_name, api_id, api_hash)

async def main():
    await client.start()
    me = await client.get_me()
    print(f"Юзер: {me.first_name} ({me.username})")

    @client.on(events.NewMessage())
    async def handler(event):
        chat_id = str(event.chat_id)
        message_id = event.message.id

        # Пропускаємо старі повідомлення
        if chat_id in last_messages and message_id <= last_messages[chat_id]:
            return

        # Отримуємо ключ для mapping (username або chat_id)
        key = event.chat.username if event.chat and event.chat.username in channel_mapping else chat_id
        topic_ids = channel_mapping.get(key)

        if not topic_ids:
            print(f"❌ Не знайдено гілки для {chat_id}")
            return

        # Якщо одне число — перетворюємо на список
        if not isinstance(topic_ids, list):
            topic_ids = [topic_ids]

        # Надсилання в усі гілки
        for topic_id in topic_ids:
            try:
                await client.send_message(
                    entity=DEST_CHANNEL_ID,
                    message=event.message,
                    reply_to=topic_id
                )
                print(f"✅ Повідомлення з {chat_id} надіслано в гілку {topic_id}")
            except Exception as e:
                print(f"⚠️ Помилка надсилання в гілку {topic_id}: {e}")

        # Зберігаємо ID останнього повідомлення
        save_last_message(chat_id, message_id)

    print("📡 Парсер працює...")
    await client.run_until_disconnected()

client.loop.run_until_complete(main())
