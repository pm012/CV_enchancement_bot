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

# Init of  Gemini service
llm_service = GeminiChatService(token=GEMINI_TOKEN)

# Register strategies
MODES = {
    "cover_letter": CoverLetterMode(llm_service),
    "linkedin": LinkedInMode(llm_service),
    "summary": ResumeSummaryMode(llm_service),
    "review": ResumeReviewMode(llm_service),
}

# Tool buttons in the main menu
ACTION_BUTTONS = {
    "mode_review": "🔍 Audit Resume vs Vacancy",
    "mode_cover_letter": "📝 Create Cover Letter",
    "mode_linkedin": "📊 Optimize LinkedIn Profile",
    "mode_summary": "📋 Match Analysis",
    "cmd_restart": "🔄 Restart / New CV",
}

TELEGRAM_COMMANDS = {
    "start": "Main menu / Restart",
    "review": "Audit of resume (CV) for vacancy",
    "cover_letter": "Generate Cover Letter",
    "linkedin": "Optmize LinkedIn",
    "summary": "Match assesment (Match evaluation)",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resets context and starts step-by-step collection of CV and vacancy."""
    context.user_data.clear()
    context.user_data["step"] = "WAITING_CV"

    await show_main_menu(update, context, TELEGRAM_COMMANDS)
    await send_photo(update, context, "AI-Resume-welcomescreen.png")

    welcome_msg = load_resource_text("text", "welcome.txt") or (
        "<b>Greetings!!! I'm your personal AI Career Assistant!</b>\n\n"
        "Step 1 out of 2: Please, <b>upload your CV</b> (.pdf / .docx) or sent it as a text:"
    )
    await send_text(update, context, welcome_msg)


async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles texts and documents depending from current state/mode (step)."""
    user_text = update.message.text
    if user_text and user_text.startswith("Restart / Back to Main Menu"):
        await start(update, context)
        return

    step = context.user_data.get("step")

    # Крок 1: Awating for CV
    if step == "WAITING_CV":
        if update.message.document:
            doc_file = await update.message.document.get_file()
            file_bytes = await doc_file.download_as_bytearray()
            cv_text = extract_text_from_file(bytes(file_bytes), update.message.document.file_name)
        else:
            cv_text = update.message.text

        if not cv_text:
            await send_text(update, context, "Not able to read the text. Please, send '.pdf'/'.docx' file  or paste text.")
            return

        context.user_data["cv_text"] = cv_text
        context.user_data["step"] = "WAITING_VACANCY"

        send_vacancy_msg = load_resource_text("text", "send_vacancy.txt") or (
            "\u2705 <b>CV was successfully saved!</b>\n\n"
            "Step 2 out of 2: Now send <b>vacansy description</b> (Job Description):"
        )
        await send_text(update, context, send_vacancy_msg)

    # Step 2: Awaiting Vacancy
    elif step == "WAITING_VACANCY":
        vacancy_text = update.message.text
        if not vacancy_text:
            await send_text(update, context, "\u26A0\uFE0F Please, send job description as a text.")
            return

        context.user_data["vacancy_text"] = vacancy_text
        context.user_data["step"] = "MAIN_MENU"

        main_menu_msg = load_resource_text("text", "main_menu.txt") or (
            "🎉 <b>Well done! Your CV and job description were successfully saved.</b>\n\n"
            "Now you can select any of available tools(options) below! No need to upload CV or text description of job again!"
        )
        await send_buttons(update, context, main_menu_msg, ACTION_BUTTONS)

    # Re-display menu after loading documents
    elif step == "MAIN_MENU":
        await send_buttons(
            update, 
            context, 
            "Context is saved! Select required action or press <b>Restart</b> to load new documents:", 
            ACTION_BUTTONS
        )

    else:
        await send_text(update, context, "Please, press /start to start from scratch.")


async def execute_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE, mode_key: str):
    """Calls choosen stretegy and displayes result with safe parser."""
    strategy = MODES.get(mode_key)
    if not strategy:
        return

    if not context.user_data.get("cv_text") or not context.user_data.get("vacancy_text"):
        await send_text(update, context, "\u26A0\uFE0F Please, load your CV and job description at first. Press /start.")
        return

    if getattr(strategy, "image_filename", None):
        await send_photo(update, context, strategy.image_filename)

    status_msg = await send_text(update, context, "🤖 <i>AI makes analysis of your data and generates resonse. Please hold a moment to get resonse...</i>")

    try:
        result = await strategy.execute(update, context)
        
        # Attempt to send with  Markdown formatting
        try:
            await status_msg.edit_text(result, parse_mode=ParseMode.MARKDOWN)
        except BadRequest as e:
            # If Telegram don't accept unclosed tags Markdown, send as a plain text
            print(f"Markdown parsing failed, sending raw text: {e}")
            await status_msg.edit_text(result, parse_mode=None)

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Got an error during processing: {e}")

    await send_buttons(update, context, "<b>What are you going to select?</b>", ACTION_BUTTONS)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles selecting Inline-buttons."""
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
    """Handles commands from the Telegram menu (/review, /cover_letter тощо)."""
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

    # Hendlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["review", "cover_letter", "linkedin", "summary"], command_menu_handler))
    app.add_handler(CallbackQueryHandler(handle_callback_query, pattern="^(mode_|cmd_restart)"))
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_user_input))

    print("Bot is up and running with stateful architecture...")
    app.run_polling()


if __name__ == "__main__":
    main()