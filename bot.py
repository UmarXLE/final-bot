import asyncio
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from handlers import commands, callback  # Убедись, что эти файлы есть и в них есть router

async def main():
    # Загрузка переменных окружения
    load_dotenv()
    token = os.getenv('BOT_TOKEN')

    if not token:
        print("❌ BOT_TOKEN не найден в .env")
        return

    # Создание экземпляра бота и диспетчера
    bot = Bot(token)
    dp = Dispatcher()

    # Создание папки для загрузок, если её нет
    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    # Подключение роутеров
    dp.include_router(commands.router)
    dp.include_router(callback.router)
    # Регистрация хэндлеров

    print("✅ Bot Started")
    try:
        await dp.start_polling(bot)
    except Exception as ex:
        print(f"❌ There is an Exception: {ex}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('👋 Bot Stopped')
