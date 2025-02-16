from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from datetime import time, datetime
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
    job = context.job
    reminder_id = job.data.get('id')
    reminders = load_reminders()
    
    if reminder_id in reminders and reminders[reminder_id]['enabled']:
        await context.bot.send_message(
            chat_id=job.chat_id,
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
    """Добавление нового напоминания"""
    # Проверяем, начинаем ли мы новое добавление
    if not context.user_data.get('adding_reminder'):
        context.user_data['adding_reminder'] = True
        await update.message.reply_text(
            'Введите текст напоминания:',
            reply_markup=ReplyKeyboardRemove()
        )
        return ADDING_REMINDER

    # Получаем введенный текст и сохраняем напоминание
    reminder_text = update.message.text
    reminders = load_reminders()
    
    new_reminder_id = f"custom_reminder_{len(reminders) + 1}"
    reminders[new_reminder_id] = {
        "text": reminder_text,
        "time": "12:00",  # время по умолчанию
        "days": "daily",
        "enabled": True
    }
    
    save_reminders(reminders)
    context.user_data['adding_reminder'] = False
    
    await update.message.reply_text(
        f"Напоминание добавлено!\n"
        f"Текст: {reminder_text}\n"
        f"Время: 12:00\n"
        f"Частота: Ежедневно"
    )
    
    # Обновляем планировщик для нового напоминания
    setup_reminder_job(context.application, new_reminder_id, reminders[new_reminder_id], update.effective_chat.id)
    
    return CHOOSING_ACTION
    
    elif context.user_data['adding_step'] == 'text':
        context.user_data['reminder_text'] = update.message.text
        context.user_data['adding_step'] = 'time'
        await update.message.reply_text('Введите время в формате ЧЧ:ММ (например, 14:30):')
        return ADDING_REMINDER
    
    elif context.user_data['adding_step'] == 'time':
        try:
            time_str = update.message.text
            hours, minutes = map(int, time_str.split(':'))
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError
            
            context.user_data['reminder_time'] = time_str
            keyboard = [['Ежедневно'], ['По будням'], ['Каждые 3 дня'], ['Каждые 7 дней']]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            context.user_data['adding_step'] = 'frequency'
            await update.message.reply_text('Выберите частоту напоминания:', reply_markup=reply_markup)
            return ADDING_REMINDER
            
        except ValueError:
            await update.message.reply_text('Неверный формат времени. Попробуйте снова (например, 14:30):')
            return ADDING_REMINDER
    
    elif context.user_data['adding_step'] == 'frequency':
        frequency = update.message.text
        reminders = load_reminders()
        
        new_reminder_id = f"custom_reminder_{len(reminders) + 1}"
        new_reminder = {
            "text": context.user_data['reminder_text'],
            "time": context.user_data['reminder_time'],
            "enabled": True
        }
        
        if frequency == 'Ежедневно':
            new_reminder['days'] = 'daily'
        elif frequency == 'По будням':
            new_reminder['days'] = 'weekdays'
        elif frequency.startswith('Каждые'):
            days = int(frequency.split()[1])
            new_reminder['interval_days'] = days
        
        reminders[new_reminder_id] = new_reminder
        save_reminders(reminders)
        
        # Очистка данных
        context.user_data.clear()
        
        await update.message.reply_text(
            f"Напоминание добавлено!\n"
            f"Текст: {new_reminder['text']}\n"
            f"Время: {new_reminder['time']}\n"
            f"Частота: {frequency}"
        )
        
        # Перезапуск планировщика для нового напоминания
        setup_reminder_job(context.application, new_reminder_id, new_reminder, update.effective_chat.id)
        
        return await start(update, context)

async def remove_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление напоминания"""
    if 'removing' not in context.user_data:
        reminders = load_reminders()
        keyboard = [[f"Удалить: {reminder['text'][:30]}..."] for reminder in reminders.values()]
        keyboard.append(['Отмена'])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        context.user_data['removing'] = True
        await update.message.reply_text('Выберите напоминание для удаления:', reply_markup=reply_markup)
        return REMOVING_REMINDER
    
    text = update.message.text
    if text == 'Отмена':
        context.user_data.clear()
        return await start(update, context)
    
    text = text.replace("Удалить: ", "").replace("...", "")
    reminders = load_reminders()
    for rid, reminder in reminders.items():
        if reminder['text'].startswith(text):
            del reminders[rid]
            save_reminders(reminders)
            context.user_data.clear()
            await update.message.reply_text("Напоминание удалено!")
            return await start(update, context)
    
    await update.message.reply_text("Напоминание не найдено.")
    context.user_data.clear()
    return await start(update, context)

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
            return await start(update, context)
    
    await update.message.reply_text("Напоминание не найдено.")
    return await start(update, context)

def setup_reminder_job(application, reminder_id, reminder, chat_id):
    """Настройка отдельного напоминания"""
    hour, minute = map(int, reminder['time'].split(':'))
    dubai_tz = pytz.timezone('Asia/Dubai')
    reminder_time = time(hour=hour, minute=minute, tzinfo=dubai_tz)
    
    job_queue = application.job_queue
    
    if 'interval_days' in reminder:
        job_queue.run_repeating(
            send_reminder,
            interval=reminder['interval_days'] * 86400,
            first=reminder_time,
            data={'id': reminder_id},
            chat_id=chat_id
        )
    elif reminder['days'] == 'daily':
        job_queue.run_daily(
            send_reminder,
            time=reminder_time,
            data={'id': reminder_id},
            chat_id=chat_id
        )
    else:  # weekdays
        job_queue.run_daily(
            send_reminder,
            time=reminder_time,
            days=(0, 1, 2, 3, 4),
            data={'id': reminder_id},
            chat_id=chat_id
        )

def setup_jobs(application, chat_id):
    """Настройка всех напоминаний"""
    reminders = load_reminders()
    for reminder_id, reminder in reminders.items():
        if reminder['enabled']:
            setup_reminder_job(application, reminder_id, reminder, chat_id)

def main():
    """Запуск бота"""
    token = "7636715892:AAEkj394bXuxJIrumZsj19zuXyZ7ntU-SHc"
    
    if not token:
        raise RuntimeError("BOT_TOKEN не установлен!")

    application = Application.builder().token(token).build()
    
    # Настройка часового пояса
    job_queue = application.job_queue
    job_queue.scheduler.timezone = pytz.timezone('Asia/Dubai')
    
    chat_id = os.environ.get("CHAT_ID", "YOUR_CHAT_ID_HERE")

    # Настройка обработчиков команд
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('show', show_reminders),
            CommandHandler('add', add_reminder),
            CommandHandler('remove', remove_reminder),
            CommandHandler('toggle', toggle_reminder)
        ],
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
        fallbacks=[MessageHandler(filters.Regex('^Отмена$'), start)]
    )

    application.add_handler(conv_handler)
    
    # Настройка напоминаний
    setup_jobs(application, chat_id)

    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()