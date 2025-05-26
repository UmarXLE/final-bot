import os
import yt_dlp
import shutil
import asyncio
import threading
from aiogram.types import FSInputFile

# --- КУКИ для yt_dlp (из переменной окружения COOKIE_DATA)
COOKIE_FILE = "cookies.txt"
cookie_data = os.getenv("COOKIE_DATA")

if cookie_data:
    with open(COOKIE_FILE, "w") as f:
        f.write(cookie_data)

# --- Генератор ID для ссылок
def generate_url_id(url: str):
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()

# --- Обновление сообщения с прогрессом
async def update_progress_message(bot, chat_id, message_id, percent):
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"Загрузка: {percent:.1f}%"
        )
    except Exception:
        pass  # Игнорируем ошибки (например, слишком частое обновление)

# --- Получение настроек yt_dlp
def get_ydl_opts(media_type, progress_hook=None):
    ffmpeg = shutil.which("ffmpeg")
    ffmpeg_installed = ffmpeg is not None

    base_opts = {
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'progress_hooks': [progress_hook] if progress_hook else [],
    }

    if os.path.exists(COOKIE_FILE):
        base_opts['cookiefile'] = COOKIE_FILE

    if media_type == "video":
        base_opts['format'] = (
            'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]' if ffmpeg_installed
            else 'best[ext=mp4]/best'
        )
        base_opts['merge_output_format'] = 'mp4'
    else:
        base_opts['format'] = 'bestaudio[ext=m4a]/bestaudio'

    return base_opts

# --- Главная функция загрузки и отправки
async def download_and_send_media(bot, chat_id, url, media_type):
    # Создаем папку downloads/, если её нет
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    sent_message = await bot.send_message(chat_id, "Загрузка: 0%")

    loop = asyncio.get_event_loop()

    def progress_hook(d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            downloaded_bytes = d.get('downloaded_bytes', 0)
            percent = downloaded_bytes / total_bytes * 100
            asyncio.run_coroutine_threadsafe(
                update_progress_message(bot, chat_id, sent_message.message_id, percent),
                loop
            )

    ydl_opts = get_ydl_opts(media_type, progress_hook)

    filename = None
    try:
        # Скачиваем видео в отдельном потоке, чтобы не блокировать event loop
        def run_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        thread = threading.Thread(target=run_download)
        thread.start()
        thread.join()

        # Получаем путь к скачанному файлу
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            filename = ydl.prepare_filename(info)

        # Уточняем расширение
        if media_type == "video" and not filename.endswith(".mp4"):
            filename = filename.rsplit(".", 1)[0] + ".mp4"
        elif media_type == "audio" and not filename.endswith(".m4a"):
            filename = filename.rsplit(".", 1)[0] + ".m4a"

        # Отправляем пользователю
        media_file = FSInputFile(filename)

        if media_type == 'video':
            await bot.send_video(chat_id, media_file, caption="🎥 Видео загружено!")
        else:
            await bot.send_audio(chat_id, media_file, caption="🎧 Аудио загружено!")

        os.remove(filename)
        await bot.delete_message(chat_id, sent_message.message_id)

    except Exception as e:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=sent_message.message_id,
            text=f"❌ Ошибка: {e}"
        )
