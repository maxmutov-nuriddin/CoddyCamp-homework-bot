from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import aiohttp

TOKEN = '7342199254:AAEaBQVpw5Ug87sYgegJG5E22RKXpZPauFU'
ADMIN_ID = 1604384939
MOCKAPI_URL = 'https://67056516031fd46a830fca90.mockapi.io/chat_users'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Привет! ✨\nОтправьте своё сообщение — мы получим его и передадим администратору. 🔔'
    )

async def forward_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat.id
    message_text = update.message.text or update.message.caption or "<Без текста>"

    # Сохраняем только текст или caption в MockAPI
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(MOCKAPI_URL, json={"user_id": user_id, "message": message_text})
        except Exception as e:
            await update.message.reply_text(f'⚠️ Ошибка при отправке на MockAPI: {e}')

    prefix = f'Сообщение от пользователя {user_id}:'

    try:
        if update.message.text:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f'{prefix}\n\n{update.message.text}')
        elif update.message.document:
            await context.bot.send_document(chat_id=ADMIN_ID, document=update.message.document.file_id, caption=f'{prefix} {update.message.caption or ""}')
        elif update.message.photo:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=f'{prefix} {update.message.caption or ""}')
        elif update.message.video:
            await context.bot.send_video(chat_id=ADMIN_ID, video=update.message.video.file_id, caption=f'{prefix} {update.message.caption or ""}')
        elif update.message.audio:
            await context.bot.send_audio(chat_id=ADMIN_ID, audio=update.message.audio.file_id, caption=f'{prefix} {update.message.caption or ""}')
        elif update.message.voice:
            await context.bot.send_voice(chat_id=ADMIN_ID, voice=update.message.voice.file_id, caption=f'{prefix} {update.message.caption or ""}')
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f'{prefix} (Неизвестный тип сообщения)')
        
        await update.message.reply_text('✅ Ваше сообщение (или файл) отправлено администратору!')
    except Exception as e:
        await update.message.reply_text(f'⚠️ Ошибка при пересылке админу: {e}')


async def forward_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat.id != ADMIN_ID:
        return

    if update.message.text:
        parts = update.message.text.split(maxsplit=1)
        user_id = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else None
        message_to_user = parts[1] if len(parts) > 1 else ""

        if user_id and message_to_user:
            await context.bot.send_message(chat_id=user_id, text=f'Ответ от администратора:\n\n{message_to_user}')
            await context.bot.send_message(chat_id=ADMIN_ID, text=f'Сообщение отправлено {user_id}.')
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text='Ошибка: не удалось распознать ID или сообщение.')

    elif update.message.document:
        user_id = int(update.message.caption.split()[0]) if update.message.caption else None
        if user_id:
            try:
                await context.bot.send_document(chat_id=user_id, document=update.message.document.file_id)
                await context.bot.send_message(chat_id=ADMIN_ID, text=f'Документ отправлен {user_id}.')
            except Exception as e:
                await context.bot.send_message(chat_id=ADMIN_ID, text=f'Ошибка при отправке документа: {e}')

    elif update.message.photo:
        user_id = int(update.message.caption.split()[0]) if update.message.caption else None
        if user_id:
            try:
                await context.bot.send_photo(chat_id=user_id, photo=update.message.photo[-1].file_id)
                await context.bot.send_message(chat_id=ADMIN_ID, text=f'Фото отправлено {user_id}.')
            except Exception as e:
                await context.bot.send_message(chat_id=ADMIN_ID, text=f'Ошибка при отправке фото: {e}')


def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    # 👇 Принимаем все сообщения от пользователей, кроме команд и сообщений от админа
    application.add_handler(MessageHandler(~filters.COMMAND & ~filters.User(ADMIN_ID), forward_user_message))

    # 👇 Обработчик для сообщений от админа
    application.add_handler(MessageHandler(filters.User(ADMIN_ID), forward_admin_message))

    application.run_polling()

if __name__ == '__main__':
    main()
