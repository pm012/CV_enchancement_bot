import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from llm_genai import GeminiChatService
from util import (
    extract_text_from_file,
    send_text,
    send_buttons,
    send_photo,
    show_main_menu,
    load_resource_text,
)

from telegram.constants import ParseMode
from telegram.error import BadRequest
from modes.cover_letter import CoverLetterMode
from modes.linkedin import LinkedInMode
from modes.resume_summary import ResumeSummaryMode
from modes.resume_review import ResumeReviewMode

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_TOKEN = os.getenv("GEMINI_API_KEY")

# Ініціалізація сервісу Gemini
llm_service = GeminiChatService(token=GEMINI_TOKEN)

# Реєстрація стратегій
MODES = {
    "cover_letter": CoverLetterMode(llm_service),
    "linkedin": LinkedInMode(llm_service),
    "summary": ResumeSummaryMode(llm_service),
    "review": ResumeReviewMode(llm_service),
}

# Кнопки інструментів у головному меню
ACTION_BUTTONS = {
    "mode_review": "🔍 Audit Resume vs Vacancy",
    "mode_cover_letter": "📝 Create Cover Letter",
    "mode_linkedin": "📊 Optimize LinkedIn Profile",
    "mode_summary": "📋 Match Analysis",
    "cmd_restart": "🔄 Restart / New CV",
}

TELEGRAM_COMMANDS = {
    "start": "Головне меню / Почати заново",
    "review": "Аудит резюме під вакансію",
    "cover_letter": "Згенерувати Cover Letter",
    "linkedin": "Оптимізувати LinkedIn",
    "summary": "Оцінка відповідності (Match)",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скидає контекст і починає покроковий збір CV та вакансії."""
    context.user_data.clear()
    context.user_data["step"] = "WAITING_CV"

    await show_main_menu(update, context, TELEGRAM_COMMANDS)
    await send_photo(update, context, "AI-Resume-welcomescreen.png")

    welcome_msg = load_resource_text("text", "welcome.txt") or (
        "<b>Вітаю у вашому AI Career Assistant! 🚀</b>\n\n"
        "Крок 1 з 2: Будь ласка, <b>завантажте ваше CV</b> (.pdf / .docx) або надішліть його текстом:"
    )
    await send_text(update, context, welcome_msg)


async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє тексти та документи в залежності від поточного стану (step)."""
    user_text = update.message.text
    if user_text and user_text.startswith("Restart / Back to Main Menu"):
        await start(update, context)
        return

    step = context.user_data.get("step")

    # Крок 1: Очікуємо CV
    if step == "WAITING_CV":
        if update.message.document:
            doc_file = await update.message.document.get_file()
            file_bytes = await doc_file.download_as_bytearray()
            cv_text = extract_text_from_file(bytes(file_bytes), update.message.document.file_name)
        else:
            cv_text = update.message.text

        if not cv_text:
            await send_text(update, context, "⚠️ Не вдалося зчитати текст. Будь ласка, надішліть `.pdf`/`.docx` файл або вставте текст.")
            return

        context.user_data["cv_text"] = cv_text
        context.user_data["step"] = "WAITING_VACANCY"

        send_vacancy_msg = load_resource_text("text", "send_vacancy.txt") or (
            "✅ <b>Резюме збережено!</b>\n\n"
            "Крок 2 з 2: Тепер надішліть <b>опис вакансії</b> (Job Description):"
        )
        await send_text(update, context, send_vacancy_msg)

    # Крок 2: Очікуємо Вакансію
    elif step == "WAITING_VACANCY":
        vacancy_text = update.message.text
        if not vacancy_text:
            await send_text(update, context, "⚠️ Будь ласка, надішліть опис вакансії текстом.")
            return

        context.user_data["vacancy_text"] = vacancy_text
        context.user_data["step"] = "MAIN_MENU"

        main_menu_msg = load_resource_text("text", "main_menu.txt") or (
            "🎉 <b>Чудово! Ваше CV та опис вакансії збережено.</b>\n\n"
            "Тепер ви можете вільно обирати будь-який інструмент нижче — повторно завантажувати документи не потрібно!"
        )
        await send_buttons(update, context, main_menu_msg, ACTION_BUTTONS)

    # Постійне меню після завантаження документів
    elif step == "MAIN_MENU":
        await send_buttons(
            update, 
            context, 
            "Контекст збережено! Оберіть потрібну дію або натисніть <b>Restart</b> для завантаження нових документів:", 
            ACTION_BUTTONS
        )

    else:
        await send_text(update, context, "Будь ласка, натисніть /start щоб розпочати спочатку.")


async def execute_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE, mode_key: str):
    """Викликає вибрану стратегію та відображає результат з безпечним парсингом."""
    strategy = MODES.get(mode_key)
    if not strategy:
        return

    if not context.user_data.get("cv_text") or not context.user_data.get("vacancy_text"):
        await send_text(update, context, "⚠️ Будь ласка, спочатку завантажте CV та вакансію. Натисніть /start.")
        return

    if getattr(strategy, "image_filename", None):
        await send_photo(update, context, strategy.image_filename)

    status_msg = await send_text(update, context, "🤖 <i>ШІ аналізує ваші дані та генерує відповідь, зачекайте...</i>")

    try:
        result = await strategy.execute(update, context)
        
        # Спроба відправити з форматуванням Markdown
        try:
            await status_msg.edit_text(result, parse_mode=ParseMode.MARKDOWN)
        except BadRequest as e:
            # Якщо Telegram сваряться на не закриті теги Markdown, надсилаємо як звичайний текст
            print(f"Markdown parsing failed, sending raw text: {e}")
            await status_msg.edit_text(result, parse_mode=None)

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Виникла помилка під час обробки: {e}")

    await send_buttons(update, context, "<b>Що бажаєте зробити далі?</b>", ACTION_BUTTONS)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє натискання Inline-кнопок."""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "cmd_restart":
        await start(update, context)
        return

    if action.startswith("mode_"):
        mode_key = action.replace("mode_", "").strip()
        await execute_strategy(update, context, mode_key)


async def command_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє команди з меню Telegram (/review, /cover_letter тощо)."""
    cmd_map = {
        "/review": "review",
        "/cover_letter": "cover_letter",
        "/linkedin": "linkedin",
        "/summary": "summary",
    }
    mode_key = cmd_map.get(update.message.text)
    if mode_key:
        await execute_strategy(update, context, mode_key)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Хендлери
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["review", "cover_letter", "linkedin", "summary"], command_menu_handler))
    app.add_handler(CallbackQueryHandler(handle_callback_query, pattern="^(mode_|cmd_restart)"))
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_user_input))

    print("Bot is up and running with stateful architecture...")
    app.run_polling()


if __name__ == "__main__":
    main()