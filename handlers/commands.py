from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hlink

import keyboards.inline_kb as in_kb
import handlers.function as hf
import url_storage as storage

router = Router()

REQUIRED_CHANNEL = '@supasupa212'  # твой канал

def contains_valid_link(text: str) -> bool:
    if not text:
        return False
    text = text.lower()
    return any(domain in text for domain in ["tiktok.com", "youtube.com", "youtu.be"])

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.reply(
        "Привет! Отправь мне ссылку на видео из ТикТока или Ютуба и я помогу тебе скачать его!"
    )

@router.message(lambda message: contains_valid_link(message.text))
async def video_request(message: Message, bot):
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, message.from_user.id)
        if member.status in ["left", "kicked"]:
            channel_link = hlink('по этой ссылке', f'https://t.me/{REQUIRED_CHANNEL.lstrip("@")}')
            await message.answer(
                f"🔒 Чтобы скачать видео, подпишись на наш канал {channel_link} и нажми /start",
                parse_mode='HTML'
            )
            return
    except Exception:
        await message.answer(
            "❗ Произошла ошибка при проверке подписки. Пожалуйста, попробуйте позже."
        )
        return

    url = message.text.strip()
    url_id = hf.generate_url_id(url)
    storage.url_storage[url_id] = url
    storage.save_url_storage(storage.url_storage)
    storage.url_storage = storage.load_url_storage()

    await message.answer("Выберите формат загрузки:", reply_markup=await in_kb.format_btn(url_id))

@router.message()
async def handle_invalid(message: Message):
    await cmd_start(message)
