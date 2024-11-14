import logging
import asyncio
import sqlite3
from telethon import TelegramClient, events
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# =======================
# Конфигурация и Настройки
# =======================

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

# Параметры для Telethon
API_ID = 29309300  # Замените на ваш API ID (целое число)
API_HASH = '6f6b0a1089c18bb2c0b87b5283133e69'  # Замените на ваш API Hash

# Параметры для aiogram
API_TOKEN = "7557679393:AAFYfkznRSAB_V0VKbuJVNamJWZ3KjZKKUw"  # Замените на ваш реальный токен бота

# Ваши Telegram ID администраторов
ADMIN_IDS = {6754669814}  # Добавьте сюда Telegram ID всех администраторов

# Список каналов для мониторинга через Telethon
CHANNELS = ['@jffiitxitxxti']  # Замените на реальные каналы

# =======================
# Инициализация Ботов и Клиентов
# =======================

# Инициализация бота aiogram
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Инициализация клиента Telethon
client = TelegramClient('session_name', API_ID, API_HASH, proxy=('socks4', '171.253.49.225', 1080))

# =======================
# Инициализация Базы Данных SQLite
# =======================

# Подключение к базе данных SQLite
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Создание таблицы authorized_users, если она не существует
cursor.execute("""
    CREATE TABLE IF NOT EXISTS authorized_users (
        user_id INTEGER PRIMARY KEY
    )
""")
conn.commit()

# Функция для загрузки авторизованных пользователей
def load_authorized_users():
    cursor.execute("SELECT user_id FROM authorized_users")
    return {row[0] for row in cursor.fetchall()}

# Загрузка авторизованных пользователей из базы данных
authorized_users = load_authorized_users()

# Функция для добавления нового пользователя в базу данных
def add_user_to_db(user_id):
    try:
        cursor.execute("INSERT OR IGNORE INTO authorized_users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        authorized_users.add(user_id)  # Добавляем пользователя в набор
        logging.info(f"Пользователь {user_id} добавлен в базу данных.")
    except Exception as e:
        logging.error(f"Ошибка при добавлении пользователя в базу данных: {e}")

# =======================
# Обработчики Команд
# =======================

# Обработчик команды /start
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer("Привет! Используйте /register для регистрации.")

# Обработчик команды /register для регистрации пользователей
@dp.message(Command("register"))
async def register_user(message: types.Message):
    if message.from_user:
        user_id = message.from_user.id
        logging.info(f"Получена команда /register от пользователя {user_id}")
        add_user_to_db(user_id)
        await message.answer("Вы успешно зарегистрированы для получения уведомлений!")
    else:
        logging.warning("Сообщение не содержит информации о пользователе.")
        await message.answer("Не удалось идентифицировать пользователя.")



    # Извлечение текста сообщения для рассылки
    args = message.text.partition(' ')[2]
    if not args:
        await message.reply("Пожалуйста, укажите сообщение для рассылки.\nПример: /broadcast Привет всем!")
        return

    broadcast_text = args
    logging.info(f"Админ {user_id} инициировал рассылку: {broadcast_text}")

    # Рассылка сообщения всем зарегистрированным пользователям
    failed_users = []
    for uid in authorized_users:
        try:
            await bot.send_message(uid, broadcast_text)
            await asyncio.sleep(0.05)  # Небольшая задержка, чтобы избежать ограничения по скорости
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {uid}: {e}")
            failed_users.append(uid)

    success_count = len(authorized_users) - len(failed_users)
    await message.reply(f"Рассылка завершена.\nУспешно отправлено: {success_count}\nНе удалось отправить: {len(failed_users)}")

    if failed_users:
        logging.info(f"Пользователи, которым не удалось отправить сообщение: {failed_users}")

# Обработчик всех остальных сообщений от администраторов как рассылки
@dp.message()
async def admin_broadcast(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        # Не админ, игнорируем сообщение
        return

    # Рассматриваем всё сообщение как рассылку
    broadcast_text = message.text
    if not broadcast_text:
        return

    logging.info(f"Админ {user_id} отправляет рассылку: {broadcast_text}")

    # Рассылка сообщения всем зарегистрированным пользователям
    failed_users = []
    for uid in authorized_users:
        try:
            await bot.send_message(uid, broadcast_text)
            await asyncio.sleep(0.05)  # Небольшая задержка, чтобы избежать ограничения по скорости
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение пользователю {uid}: {e}")
            failed_users.append(uid)

    success_count = len(authorized_users) - len(failed_users)
    await message.reply(f"Рассылка завершена.\nУспешно отправлено: {success_count}\nНе удалось отправить: {len(failed_users)}")

    if failed_users:
        logging.info(f"Пользователи, которым не удалось отправить сообщение: {failed_users}")

# =======================
# Telethon Обработчики
# =======================

# Функция для отправки постов пользователям через aiogram
async def send_post_to_users(post):
    try:
        for user_id in authorized_users:
            await bot.send_message(user_id, post)
            await asyncio.sleep(0.05)  # Небольшая задержка
        logging.info("Пост успешно отправлен пользователям.")
    except Exception as e:
        logging.error(f"Ошибка при отправке поста пользователям: {e}")

# Обработчик новых сообщений в каналах
@client.on(events.NewMessage(chats=CHANNELS))
async def new_message_listener(event):
    message = event.message.message
    logging.info(f"Новое сообщение получено в канале: {message}")

    # Отправка сообщения всем зарегистрированным пользователям
    await send_post_to_users(message)

# =======================
# Основная Асинхронная Функция
# =======================

async def main():
    # Запуск клиента Telethon
    await client.start()
    logging.info("Клиент Telethon запущен и ожидает новых сообщений.")

    # Запуск aiogram Dispatcher и Telethon одновременно
    telethon_task = asyncio.create_task(client.run_until_disconnected())
    aiogram_task = asyncio.create_task(dp.start_polling(bot))

    logging.info("Запущены процессы Telethon и aiogram.")
    await asyncio.gather(telethon_task, aiogram_task)

# =======================
# Запуск Бота
# =======================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")
    finally:
        conn.close()
