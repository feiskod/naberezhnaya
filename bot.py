import pytz
import os
from datetime import time as dt_time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from telegram.ext import CommandHandler

# Конфигурация (ЗАМЕНИТЕ!)
TOKEN = os.getenv("TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_poll(context)

# Хранилище данных
participants = {}
summary_msg_id = None

async def send_poll(context: ContextTypes.DEFAULT_TYPE):
    """Отправка опроса в группу"""
    global summary_msg_id
    print("🔔 send_poll() вызван по расписанию!")
    keyboard = [
        [InlineKeyboardButton("✅ Иду", callback_data="yes")],
        [InlineKeyboardButton("❌ Не иду", callback_data="no")]
    ]
    msg = await context.bot.send_message(
        chat_id=GROUP_ID,
        text="🏋️‍♂️ *Кто идёт на тренировку сегодня?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    summary_msg_id = msg.message_id
    print("✅ Опрос отправлен в группу")

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    if query.data == "no":
        participants.pop(user.id, None)
        await query.answer(f"{user.first_name} не идёт")

    elif query.data == "yes":
        # Отвечаем, чтобы убрать "часики" на кнопке
        await query.answer("Выберите время в личных сообщениях")

        # Отправляем ЛИЧНОЕ сообщение пользователю с кнопками выбора времени
        time_buttons = [
            [InlineKeyboardButton("18:00", callback_data="time_18")],
            [InlineKeyboardButton("19:00", callback_data="time_19")],
            [InlineKeyboardButton("20:00", callback_data="time_20")]
        ]
        await context.bot.send_message(
            chat_id=user.id,
            text="Выберите время тренировки:",
            reply_markup=InlineKeyboardMarkup(time_buttons)
        )
        # НЕ меняем кнопки в групповом сообщении — оставляем как есть

    elif query.data.startswith("time_"):
        time_chosen = query.data.split('_')[1]
        participants[user.id] = {
            "name": user.first_name,
            "time": f"{time_chosen}:00"
        }
        await query.answer(f"Записал на {time_chosen}:00!")

    await update_summary(context.bot)

async def update_summary(bot):
    """Обновление списка участников"""
    global summary_msg_id
    if not summary_msg_id:
        return
        
    text = "📊 *Список участников:*\n" + "\n".join(
        f"- {p['name']} в {p['time']}" for p in participants.values()
    ) if participants else "Пока никто не идёт 🏋️‍♂️"
    
    try:
        await bot.edit_message_text(
            chat_id=GROUP_ID,
            message_id=summary_msg_id,
            text=text,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"⚠️ Ошибка обновления: {e}")

from datetime import datetime, timedelta, timezone, time as dt_time

def main():
    app = Application.builder().token(TOKEN).build()
    job_queue = app.job_queue

    # Правильная установка времени на 12:40 по Новосибирску
    tz = pytz.timezone("Asia/Novosibirsk")
    run_time = dt_time(hour=13, minute=30, tzinfo=tz)

    print("📅 Планировщик опроса назначен на 13:00 по Новосибирску")

    job_queue.run_daily(
        send_poll,
        time=run_time,
        days=tuple(range(7))  # Каждый день недели
    )

    app.add_handler(CallbackQueryHandler(handle_response))
    app.add_handler(CommandHandler("test", test_command))

    print("🟢 Бот запущен. Ждём отправки опроса в 13:00 или по /test")
    app.run_polling()

if __name__ == '__main__':
    main()