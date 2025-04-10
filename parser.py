from telethon import TelegramClient, events
import json
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_name = "telegram_parser_active"

DEST_CHANNEL_ID = -1002403468473  # ID закрытого канала

# Mapping источников → ID гілок
channel_mapping = {
    os.getenv("CH_FIRST"): int(os.getenv("FORK_FIRST")),
    os.getenv("CH_SECOND"): int(os.getenv("FORK_SECOND")),
    os.getenv("CH_THIRD"): int(os.getenv("FORK_THIRD")),
    os.getenv("CH_FOURTH"): int(os.getenv("FORK_FOURTH")),
}

LAST_MESSAGES_FILE = "last_messages.json"
last_messages = {}

# Загрузка последних сообщений из файла
if os.path.exists(LAST_MESSAGES_FILE):
    with open(LAST_MESSAGES_FILE, "r") as f:
        last_messages = json.load(f)

# Асинхронная запись в файл
save_task = None

async def save_last_message(chat_id, message_id):
    last_messages[str(chat_id)] = message_id
    global save_task
    if save_task and not save_task.done():
        return
    save_task = asyncio.create_task(_write_to_file())

async def _write_to_file():
    await asyncio.sleep(1)
    with open(LAST_MESSAGES_FILE, "w") as f:
        json.dump(last_messages, f)

# Клиент с отключённой защитой от флуда
client = TelegramClient(session_name, api_id, api_hash, flood_sleep_threshold=0)

@client.on(events.NewMessage())
async def handler(event):
    if event.message.out:  # Пропустить свои сообщения
        return

    chat_id = str(event.chat_id)
    message_id = event.message.id

    # Пропускаем уже обработанные
    if chat_id in last_messages and message_id <= last_messages[chat_id]:
        return

    # Получаем ключ (username или ID)
    key = event.chat.username if event.chat and event.chat.username in channel_mapping else chat_id
    topic_ids = channel_mapping.get(key)

    if not topic_ids:
        print(f"❌ Нет гілки для {chat_id}")
        return

    if not isinstance(topic_ids, list):
        topic_ids = [topic_ids]

    for topic_id in topic_ids:
        try:
            await client.send_message(
                entity=DEST_CHANNEL_ID,
                message=event.message,
                reply_to=topic_id
            )
            print(f"✅ Переслано з {chat_id} в гілку {topic_id}")
        except Exception as e:
            print(f"⚠️ Помилка пересилки в гілку {topic_id}: {e}")

    await save_last_message(chat_id, message_id)

async def main():
    await client.start()
    me = await client.get_me()
    print(f"🟢 Підключено як {me.first_name} ({me.username})")
    print("📡 Парсер запущено...")
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
