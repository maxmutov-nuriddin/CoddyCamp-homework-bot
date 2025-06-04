from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)
import aiohttp

from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)


# === Конфигурация ===
TOKEN = '7342199254:AAEaBQVpw5Ug87sYgegJG5E22RKXpZPauFU'
ADMIN_ID = 1604384939
MOCKAPI_URL = 'https://67056516031fd46a830fca90.mockapi.io/chat_users'

# === FSM состояние ===
REPLYING = range(1)
admin_reply_targets = {}  # Словарь {admin_id: user_id}


# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Привет! ✨\nОтправьте своё сообщение — мы получим его и передадим администратору. 🔔'
    )


# === Пользователь отправил сообщение ===
async def forward_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.chat.id
    message_text = update.message.text or update.message.caption or "<Без текста>"

    # Сохраняем текст в MockAPI
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(MOCKAPI_URL, json={"user_id": user_id, "message": message_text})
        except Exception as e:
            await update.message.reply_text(f'⚠️ Ошибка при отправке на MockAPI: {e}')

    prefix = f'Сообщение от пользователя {user_id}:'
    reply_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("✉️ Ответить", callback_data=f"reply_{user_id}")
    ]])

    try:
        if update.message.text:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f'{prefix}\n\n{update.message.text}', reply_markup=reply_markup)
        elif update.message.document:
            await context.bot.send_document(chat_id=ADMIN_ID, document=update.message.document.file_id,
                                            caption=f'{prefix}\n\n{update.message.caption or ""}', reply_markup=reply_markup)
        elif update.message.photo:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id,
                                         caption=f'{prefix}\n\n{update.message.caption or ""}', reply_markup=reply_markup)
        elif update.message.video:
            await context.bot.send_video(chat_id=ADMIN_ID, video=update.message.video.file_id,
                                         caption=f'{prefix}\n\n{update.message.caption or ""}', reply_markup=reply_markup)
        elif update.message.audio:
            await context.bot.send_audio(chat_id=ADMIN_ID, audio=update.message.audio.file_id,
                                         caption=f'{prefix}\n\n{update.message.caption or ""}', reply_markup=reply_markup)
        elif update.message.voice:
            await context.bot.send_voice(chat_id=ADMIN_ID, voice=update.message.voice.file_id,
                                         caption=f'{prefix}\n\n{update.message.caption or ""}', reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f'{prefix}\n\n(Неизвестный тип сообщения)', reply_markup=reply_markup)

        await update.message.reply_text("✅ Ваше сообщение отправлено администратору!")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка при пересылке админу: {e}")


# === Обработка кнопки "Ответить" от админа ===
async def handle_reply_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query: CallbackQuery = update.callback_query
    await query.answer()

    user_id = int(query.data.split("_")[1])
    admin_reply_targets[query.from_user.id] = user_id

    await context.bot.send_message(chat_id=ADMIN_ID, text=f"✏️ Введите сообщение (текст/файл) для пользователя {user_id}:")
    return REPLYING


# === Ответ админа в состоянии REPLYING ===
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    admin_id = update.message.chat.id
    user_id = admin_reply_targets.get(admin_id)

    if not user_id:
        await update.message.reply_text("⚠️ Не выбран пользователь для ответа.")
        return ConversationHandler.END

    try:
        if update.message.text:
            await context.bot.send_message(chat_id=user_id, text=f"💬 Ответ от администратора:\n\n{update.message.text}")
        elif update.message.document:
            await context.bot.send_document(chat_id=user_id, document=update.message.document.file_id,
                                            caption=update.message.caption)
        elif update.message.photo:
            await context.bot.send_photo(chat_id=user_id, photo=update.message.photo[-1].file_id,
                                         caption=update.message.caption)
        elif update.message.video:
            await context.bot.send_video(chat_id=user_id, video=update.message.video.file_id,
                                         caption=update.message.caption)
        elif update.message.audio:
            await context.bot.send_audio(chat_id=user_id, audio=update.message.audio.file_id,
                                         caption=update.message.caption)
        elif update.message.voice:
            await context.bot.send_voice(chat_id=user_id, voice=update.message.voice.file_id,
                                         caption=update.message.caption)
        else:
            await update.message.reply_text("⚠️ Неизвестный тип сообщения.")

        await update.message.reply_text(f"✅ Сообщение отправлено пользователю {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке: {e}")

    return ConversationHandler.END


# === Основной запуск ===
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    # Пользователи: любые сообщения кроме команд и кроме админа
    application.add_handler(MessageHandler(~filters.COMMAND & ~filters.User(ADMIN_ID), forward_user_message))

    # FSM: Ответы от админа
    reply_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_reply_button, pattern=r"^reply_\d+$")],
        states={
            REPLYING: [MessageHandler(filters.User(ADMIN_ID), handle_admin_reply)]
        },
        fallbacks=[]
    )
    application.add_handler(reply_conv)

    application.run_polling()


if __name__ == '__main__':
    main()
