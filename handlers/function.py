import os
import time
import yt_dlp
import shutil
import asyncio
import threading
from aiogram.types import FSInputFile

def generate_url_id(url: str):
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()

async def update_progress_message(bot, chat_id, message_id, percent):
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"Загрузка: {percent:.1f}%"
        )
    except Exception:
        pass  # Игнорируем ошибки, например, если сообщения обновляются слишком быстро

def download_video_thread(url, media_type, ydl_opts, progress_hook):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

async def download_and_send_media(bot, chat_id, url, media_type):
    # Проверяем наличие ffmpeg
    ffmpeg = shutil.which("ffmpeg")
    ffmpeg_installed = ffmpeg is not None

    if media_type == "video":
        ydl_opts = {
            'format': (
                'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]' if ffmpeg_installed
                else 'best[ext=mp4]/best'  # если нет ffmpeg, качаем один поток
            ),
            'merge_output_format': 'mp4',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'progress_hooks': [],
        }
    else:  # аудио
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'progress_hooks': [],
        }

    # Отправляем начальное сообщение с прогрессом
    sent_message = await bot.send_message(chat_id, "Загрузка: 0%")

    loop = asyncio.get_event_loop()

    def progress_hook(d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            downloaded_bytes = d.get('downloaded_bytes', 0)
            percent = downloaded_bytes / total_bytes * 100
            # Запускаем асинхронное обновление сообщения из потока
            asyncio.run_coroutine_threadsafe(
                update_progress_message(bot, chat_id, sent_message.message_id, percent),
                loop
            )

    ydl_opts['progress_hooks'] = [progress_hook]

    # Запускаем загрузку в отдельном потоке, чтобы не блокировать цикл
    def run_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    filename = None
    try:
        thread = threading.Thread(target=run_download)
        thread.start()
        thread.join()
        # После завершения потока filename нужно получить через ydl.prepare_filename — для этого переделаем чуть ниже

        # К сожалению, чтобы получить filename, надо повторно вызвать extract_info без загрузки.
        # Поэтому для упрощения вызовем отдельно (лучше переписать на return через очередь — упрощаем):

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            filename = ydl.prepare_filename(info)

        # Корректируем расширение
        if media_type == "video" and not filename.endswith(".mp4"):
            filename = filename.rsplit(".", 1)[0] + ".mp4"
        elif media_type == "audio" and not filename.endswith(".m4a"):
            filename = filename.rsplit(".", 1)[0] + ".m4a"

        # Отправляем файл
        media_file = FSInputFile(filename)

        if media_type == 'video':
            await bot.send_video(chat_id, media_file, caption="🎥 Видео загружено!")
        else:
            await bot.send_audio(chat_id, media_file, caption="🎧 Аудио загружено!")

        os.remove(filename)
        await bot.delete_message(chat_id, sent_message.message_id)  # удаляем сообщение с прогрессом

    except Exception as e:
        await bot.edit_message_text(chat_id=chat_id, message_id=sent_message.message_id, text=f"❌ Ошибка: {e}")
