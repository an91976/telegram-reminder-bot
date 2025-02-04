import logging
import os
import time
import pytz
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Список вопросов (3 категории по 10 вопросов)
questions = [
    {
        "category": "Древний Рим",
        "question": [
            "Кто основал Рим?",
            "Как назывался главный храм Древнего Рима?",
            "Какой титул носили римские императоры?",
            "Как называлась денежная единица Древнего Рима?",
            "Как звали первого римского императора?",
            "Как назывался главный стадион Рима?",
            "Какое событие положило конец Римской империи?",
            "Какой народ разрушил Рим в 410 году?",
            "Кто убил Юлия Цезаря?",
            "Как называлась римская армия?"
        ],
        "options": [
            ["Ромул и Рем", "Цезарь", "Ганнибал", "Александр Македонский"],
            ["Парфенон", "Капитолийский храм", "Колизей", "Пантеон"],
            ["Консул", "Цезарь", "Император", "Легионер"],
            ["Динарий", "Сестерций", "Франк", "Ауреус"],
            ["Октавиан Август", "Нерон", "Цезарь", "Траян"],
            ["Колизей", "Цирк Максимус", "Театр Помпея", "Арена Вероны"],
            ["Взятие Константинополя", "Падение Рима", "Восстание Спартака", "Смерть Цезаря"],
            ["Готы", "Вандалы", "Франки", "Галлы"],
            ["Брут", "Кассий", "Цицерон", "Октавиан"],
            ["Легион", "Когорта", "Центурия", "Манипула"]
        ],
        "correct": [0, 1, 2, 0, 0, 1, 1, 0, 0, 0]
    },
    {
        "category": "Кофе",
        "question": [
            "Из какой страны пришел кофе в Европу?",
            "В каком городе открылось первое кафе в Европе?",
            "Что означает термин Specialty Coffee?",
            "Какие страны входят в 'кофейный пояс'?",
            "Какой город считается столицей кофе в Италии?",
            "Что такое эспрессо?",
            "Какой напиток готовят из кофе, молока и пенки?",
            "Как называется турецкий метод приготовления кофе?",
            "Какие зёрна используются для арабики?",
            "Какой прибор используют для варки кофе в турке?"
        ],
        "options": [
            ["Бразилия", "Египет", "Эфиопия", "Индия"],
            ["Лондон", "Париж", "Венеция", "Вена"],
            ["Особый метод обжарки", "Кофе с оценкой 80+ баллов SCA", "Экологически чистый кофе", "Кофе, сваренный только альтернативными методами"],
            ["Россия, США, Германия", "Эфиопия, Бразилия, Колумбия", "Китай, Индия, Япония", "Канада, Франция, Испания"],
            ["Рим", "Милан", "Неаполь", "Флоренция"],
            ["Сильный крепкий кофе", "Кофе с молоком", "Французский напиток", "Чай"],
            ["Капучино", "Латте", "Раф", "Мокко"],
            ["Джезва", "Френч-пресс", "Мока", "Гейзер"],
            ["Арабика", "Робуста", "Либерика", "Эксцельза"],
            ["Джезва", "Гейзерная кофеварка", "Френч-пресс", "Мока"]
        ],
        "correct": [2, 2, 1, 1, 2, 0, 0, 0, 0, 0]
    },
    {
        "category": "Вторая мировая война",
        "question": [
            "В каком году началась Вторая мировая война?",
            "Как называлась операция нападения на СССР?",
            "Кто был главнокомандующим союзников в Нормандии?",
            "Как назывался немецкий план молниеносной войны?",
            "Какое событие привело к вступлению США в войну?",
            "Как называлась крупнейшая танковая битва войны?",
            "Как назывался секретный проект создания атомной бомбы?",
            "Кто подписал капитуляцию Германии?",
            "Как называлась первая атомная бомба, сброшенная на Японию?",
            "Какой город был взят Красной Армией в 1945 году?"
        ],
        "options": [
            ["1937", "1939", "1941", "1945"],
            ["Барбаросса", "Цитадель", "Оверлорд", "Тайфун"],
            ["Дуайт Эйзенхауэр", "Уинстон Черчилль", "Шарль де Голль", "Бернард Монтгомери"],
            ["Блицкриг", "Тотальная война", "Барбаросса", "Оверлорд"],
            ["Бомбардировка Хиросимы", "Нападение на Перл-Харбор", "Оккупация Франции", "Высадка в Нормандии"],
            ["Сталинградская битва", "Курская битва", "Битва за Берлин", "Битва за Британию"],
            ["Манхэттенский проект", "Проект Тринити", "Операция Армия", "План Оверлорд"],
            ["Гитлер", "Геринг", "Кейтель", "Роммель"],
            ["Толстяк", "Малыш", "Царь-бомба", "Тринити"],
            ["Берлин", "Варшава", "Прага", "Будапешт"]
        ],
        "correct": [1, 0, 0, 0, 1, 1, 0, 2, 1, 0]
    }
]

# Словари для хранения данных игроков
player_scores = {}
player_times = {}
player_logins = {}
player_current_question = {}
all_results = {}  # Словарь для хранения всех результатов игроков

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать в викторину!\n"
        "🎮 Нажмите /quiz, чтобы начать игру.\n"
        "📜 В игре несколько категорий вопросов.\n"
        "⏱ Учитывается время ответов.\n"
        "🏆 В конце вы получите свою статистику!\n"
        "📊 /top - посмотреть таблицу рекордов"
    )

# Команда /quiz — запрос логина и инициализация викторины
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text("👤 Введите ваш логин для начала игры:")
    context.user_data["awaiting_login"] = True

# Сохранение логина и запуск викторины
async def receive_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_login"):
        user_id = update.message.from_user.id
        player_logins[user_id] = update.message.text
        player_scores[user_id] = 0
        player_times[user_id] = 0
        context.user_data["awaiting_login"] = False
        # Инициализируем индексы: текущая категория и вопрос в ней
        context.user_data["current_category"] = 0
        context.user_data["current_question"] = 0
        await ask_question(update, context)

# Функция отправки вопроса
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat_idx = context.user_data.get("current_category", 0)
    q_idx = context.user_data.get("current_question", 0)
    
    # Если закончились все категории, завершаем викторину
    if cat_idx >= len(questions):
        user_id = update.message.from_user.id
        total_questions = sum(len(cat["question"]) for cat in questions)
        final_score = player_scores[user_id]
        final_time = player_times[user_id]
        if user_id not in all_results:
            all_results[user_id] = []
        all_results[user_id].append({
            "login": player_logins[user_id],
            "score": final_score,
            "time": final_time
        })
        best_score = max(r["score"] for r in all_results[user_id])
        await update.message.reply_text(
            f"🏁 Викторина завершена!\n"
            f"👤 Логин: {player_logins[user_id]}\n"
            f"✨ Правильных ответов: {final_score} из {total_questions}\n"
            f"⏱ Общее время: {round(final_time, 2)} сек\n"
            f"🏆 Ваш лучший результат: {best_score} правильных ответов\n"
            f"📊 /top - таблица рекордов"
        )
        return

    category = questions[cat_idx]
    # Если вопросы в текущей категории закончились, переходим к следующей
    if q_idx >= len(category["question"]):
        context.user_data["current_category"] = cat_idx + 1
        context.user_data["current_question"] = 0
        await ask_question(update, context)
        return

    question_text = category["question"][q_idx]
    options = category["options"][q_idx]
    keyboard = [[InlineKeyboardButton(opt, callback_data=str(i))] for i, opt in enumerate(options)]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"📚 Категория: {category['category']}\n"
        f"❓ Вопрос {q_idx + 1}: {question_text}",
        reply_markup=reply_markup
    )
    context.user_data["start_time"] = time.time()

# Обработчик нажатий кнопок с ответами
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    cat_idx = context.user_data.get("current_category", 0)
    q_idx = context.user_data.get("current_question", 0)
    category = questions[cat_idx]
    
    elapsed_time = time.time() - context.user_data.get("start_time", time.time())
    player_times[user_id] += elapsed_time
    
    answer = int(query.data)
    correct_answer = category["correct"][q_idx]
    
    if answer == correct_answer:
        player_scores[user_id] += 1
        response = "✅ Правильно! 🎉"
    else:
        correct_opt = category["options"][q_idx][correct_answer]
        response = f"❌ Неправильно. Правильный ответ: {correct_opt}"
    
    context.user_data["current_question"] = q_idx + 1
    # Если в текущей категории ещё есть вопросы, показываем следующий
    if context.user_data["current_question"] < len(category["question"]):
        next_q = category["question"][context.user_data["current_question"]]
        next_opts = category["options"][context.user_data["current_question"]]
        keyboard = [[InlineKeyboardButton(opt, callback_data=str(i))] for i, opt in enumerate(next_opts)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=f"{response}\n\n📚 Категория: {category['category']}\n"
                 f"❓ Вопрос {context.user_data['current_question'] + 1}: {next_q}",
            reply_markup=reply_markup
        )
        context.user_data["start_time"] = time.time()
    else:
        # Переход к следующей категории
        context.user_data["current_category"] = cat_idx + 1
        context.user_data["current_question"] = 0
        await query.edit_message_text(text=response)
        # Чтобы продолжить, создаём искусственное обновление и вызываем ask_question
        # (можно также отправить новое сообщение через bot.send_message)
        await query.message.reply_text("Переходим к следующей категории...")
        await ask_question(query.message, context)

# Команда /top — вывод таблицы лидеров
async def show_top(context: ContextTypes.DEFAULT_TYPE):
    chat_id = os.environ.get("CHAT_ID")
    if not chat_id:
        logger.error("CHAT_ID не установлен!")
        return
    if not all_results:
        await context.bot.send_message(chat_id=chat_id, text="🏆 Пока нет результатов!")
        return

    all_scores = []
    for uid, results in all_results.items():
        for res in results:
            all_scores.append(res)
    sorted_scores = sorted(all_scores, key=lambda x: (-x["score"], x["time"]))
    message = "🏆 Таблица на сегодня:\n\n"
    for i, res in enumerate(sorted_scores[:10], 1):
        message += f"{i}. {res['login']}: {res['score']} правильных ответов за {round(res['time'], 2)} сек\n"
    await context.bot.send_message(chat_id=chat_id, text=message)
    all_results.clear()
    logger.info("Таблица лидеров очищена.")

def main():
    token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("BOT_TOKEN или CHAT_ID не установлены!")
    application = Application.builder().token(token).build()

    # Планировщик: отправка таблицы лидеров каждый день в 20:00 (по Москве)
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))
    scheduler.add_job(show_top, "cron", hour=20, minute=0, args=[application])
    scheduler.start()

    # Регистрация обработчиков команд и сообщений
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("top", show_top))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_login))
    application.add_handler(CallbackQueryHandler(button))
    
    logger.info("Бот запущен и планировщик активирован.")
    application.run_polling()

if __name__ == "__main__":
    main()
