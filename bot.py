from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from datetime import time
import json
import os
import pytz

# Состояния для разговора
CHOOSING_ACTION = 0
ADDING_REMINDER = 1
REMOVING_REMINDER = 2
SETTING_TIME = 3

# Структура для хранения напоминаний
DEFAULT_REMINDERS = {
    "teeth_morning": {
        "text": "Даня, ты почистил зубы? 🦷",
        "time": "06:00",
        "days": "weekdays",
        "enabled": True
    },
    "teeth_evening": {
        "text": "Даня, ты почистил зубы? 🦷",
        "time": "22:00",
        "days": "daily",
        "enabled": True
    },
    "hair_wash": {
        "text": "Даня, помой голову! 🚿",
        "time": "20:00",
        "interval_days": 3,
        "enabled": True
    },
    "nails": {
        "text": "Даня, пора подстричь ногти! ✂️",
        "time": "20:00",
        "interval_days": 7,
        "enabled": True
    }
}

def load_reminders():
    """Загрузка настроек напоминаний из файла"""
    try:
        with open('reminders.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        save_reminders(DEFAULT_REMINDERS)
        return DEFAULT_REMINDERS

def save_reminders(reminders):
    """Сохранение настроек напоминаний в файл"""
    with open('reminders.json', 'w', encoding='utf-8') as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Отправка напоминания"""
    reminder_id = context.job.data['id']
    reminders = load_reminders()
    if reminder_id in reminders and reminders[reminder_id]['enabled']:
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=reminders[reminder_id]['text']
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        ['Показать напоминания'],
        ['Добавить напоминание'],
        ['Удалить напоминание'],
        ['Включить/выключить напоминание']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        'Привет! Я бот-напоминалка. Что вы хотите сделать?',
        reply_markup=reply_markup
    )
    return CHOOSING_ACTION

async def show_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все настроенные напоминания"""
    reminders = load_reminders()
    message = "Текущие напоминания:\n\n"
    for rid, reminder in reminders.items():
        status = "✅" if reminder['enabled'] else "❌"
        time_str = reminder['time']
        if 'interval_days' in reminder:
            frequency = f"Каждые {reminder['interval_days']} дней"
        elif reminder['days'] == 'daily':
            frequency = "Ежедневно"
        else:
            frequency = "По будням"
        message += f"{status} {reminder['text']}\n   🕒 {time_str}, {frequency}\n\n"
    
    await update.message.reply_text(message)
    return CHOOSING_ACTION

async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса добавления напоминания"""
    await update.message.reply_text(
        'Введите текст напоминания:',
        reply_markup=ReplyKeyboardRemove()
    )
    return ADDING_REMINDER

async def remove_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список напоминаний для удаления"""
    reminders = load_reminders()
    keyboard = [[f"Удалить: {reminder['text'][:30]}..."] for reminder in reminders.values()]
    keyboard.append(['Отмена'])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        'Выберите напоминание для удаления:',
        reply_markup=reply_markup
    )
    return REMOVING_REMINDER

async def toggle_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включение/выключение напоминаний"""
    reminders = load_reminders()
    keyboard = [[f"Переключить: {reminder['text'][:30]}..."] for reminder in reminders.values()]
    keyboard.append(['Отмена'])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        'Выберите напоминание для включения/выключения:',
        reply_markup=reply_markup
    )
    return CHOOSING_ACTION

async def handle_reminder_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка включения/выключения напоминания"""
    text = update.message.text.replace("Переключить: ", "").replace("...", "")
    reminders = load_reminders()
    for rid, reminder in reminders.items():
        if reminder['text'].startswith(text):
            reminder['enabled'] = not reminder['enabled']
            status = "включено" if reminder['enabled'] else "выключено"
            save_reminders(reminders)
            await update.message.reply_text(f"Напоминание {status}!")
            return CHOOSING_ACTION
    
    await update.message.reply_text("Напоминание не найдено.")
    return CHOOSING_ACTION

def setup_jobs(application, chat_id):
    """Настройка расписания напоминаний"""
    reminders = load_reminders()
    dubai_tz = pytz.timezone('Asia/Dubai')
    
    for rid, reminder in reminders.items():
        hour, minute = map(int, reminder['time'].split(':'))
        reminder_time = time(hour=hour, minute=minute, tzinfo=dubai_tz)
        
        if 'interval_days' in reminder:
            application.job_queue.run_repeating(
                send_reminder,
                interval=reminder['interval_days'] * 86400,  # дни в секунды
                first=reminder_time,
                data={'id': rid},
                chat_id=chat_id
            )
        elif reminder['days'] == 'daily':
            application.job_queue.run_daily(
                send_reminder,
                time=reminder_time,
                data={'id': rid},
                chat_id=chat_id
            )
        else:  # weekdays
            application.job_queue.run_daily(
                send_reminder,
                time=reminder_time,
                days=(0, 1, 2, 3, 4),
                data={'id': rid},
                chat_id=chat_id
            )

def main():
    """Запуск бота"""
    token = "7636715892:AAEkj394bXuxJIrumZsj19zuXyZ7ntU-SHc"
    
    if not token:
        raise RuntimeError("BOT_TOKEN не установлен!")
application = Application.builder().token(token).build()
    # Сначала строим приложение
    application = builder.build()
    # Затем устанавливаем часовой пояс для планировщика
    job_queue = application.job_queue
    job_queue.scheduler.timezone = pytz.timezone('Asia/Dubai')
    
    chat_id = os.environ.get("CHAT_ID", "YOUR_CHAT_ID_HERE")

    # Настраиваем обработчики команд
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_ACTION: [
                MessageHandler(filters.Regex('^Показать напоминания$'), show_reminders),
                MessageHandler(filters.Regex('^Добавить напоминание$'), add_reminder),
                MessageHandler(filters.Regex('^Удалить напоминание$'), remove_reminder),
                MessageHandler(filters.Regex('^Включить/выключить напоминание$'), toggle_reminder),
                MessageHandler(filters.Regex('^Переключить: '), handle_reminder_toggle),
            ],
            ADDING_REMINDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_reminder)
            ],
            REMOVING_REMINDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, remove_reminder)
            ],
        },
        fallbacks=[MessageHandler(filters.Regex('^Отмена$'), start)],
    )

    application.add_handler(conv_handler)
    
    # Настраиваем расписание напоминаний
    setup_jobs(application, chat_id)

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()