import math
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

from llm_genai import GeminiChatService, GeminiQuotaExceeded
from util import (
    extract_text_from_file,
    send_text,
    send_buttons,
    send_photo,
    show_main_menu,
    load_resource_text,
    split_telegram_text,
)

from modes.cover_letter import CoverLetterMode
from modes.linkedin import LinkedInMode
from modes.resume_summary import ResumeSummaryMode
from modes.resume_review import ResumeReviewMode
from resume_pdf import create_resume_pdf

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
            "🎉 <b>CV was successfully saved!</b>\n\n"
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

    elif step == "AWAITING_ADJUSTMENT":
        correction = update.message.text
        if not correction:
            await send_text(update, context, "Please send your correction or adjustment as text.")
            return

        last_mode = context.user_data.get("last_mode")
        strategy = MODES.get(last_mode)
        if not strategy:
            await send_text(update, context, "Please select a mode again before sending an adjustment.")
            return

        adjustments = context.user_data.setdefault("mode_adjustments", [])
        if correction not in adjustments:
            adjustments.append(correction)
        await retry_saved_adjustments(update, context)

    elif step == "MAIN_MENU":
        await send_text(
            update,
            context,
            "Your CV and vacancy are ready. Use the buttons in the previous "
            "message to choose a tool.",
        )

    else:
        await send_text(update, context, "Please, press /start to start from scratch.")


async def send_mode_actions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode_key: str,
):
    """Show available actions and tell the user how to revise the result."""
    buttons = dict(ACTION_BUTTONS)
    if mode_key == "review":
        buttons["action_resume_pdf"] = "📄 Download Tailored Resume (PDF)"
    layout = (2, 2, 2) if len(buttons) == 6 else (2, 2, 1)
    await send_buttons(
        update,
        context,
        "Send a correction or adjustment as a message to refine this result. "
        "You can also select another mode below.",
        buttons,
        layout=layout,
    )


async def retry_saved_adjustments(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Apply saved corrections and offer an explicit retry when the model is unavailable."""
    mode_key = context.user_data.get("last_mode")
    strategy = MODES.get(mode_key)
    adjustments = context.user_data.get("mode_adjustments", [])
    if not strategy or not adjustments:
        await send_text(
            update,
            context,
            "There are no saved adjustments to retry. Send an adjustment after running a mode.",
        )
        return

    status_msg = await send_text(update, context, "🤖 Revising the result with your adjustments...")
    try:
        result = await strategy.refine(context, adjustments)
    except GeminiQuotaExceeded as error:
        print(f"Gemini quota exhausted while revising {mode_key} result: {error}")
        await status_msg.edit_text(
            quota_exhausted_message(error),
            parse_mode=None,
        )
        return
    except Exception as error:
        print(f"Error while revising {mode_key} result: {error}")
        await status_msg.edit_text(
            "⚠️ Gemini is temporarily unavailable. Your adjustment is saved; "
            "try again using the button below.",
            parse_mode=None,
        )
        await send_buttons(
            update,
            context,
            "Retry the saved adjustment when the AI service is available.",
            {"action_retry_adjustment": "🔁 Retry adjustment"},
            layout=(1,),
        )
        return

    context.user_data["last_result"] = result
    await send_result(status_msg, update, context, result)
    await send_mode_actions(update, context, mode_key)


def quota_exhausted_message(error: GeminiQuotaExceeded) -> str:
    """Explain the quota reset estimate and direct the user to quota settings."""
    if error.retry_after_seconds is not None:
        wait_minutes = max(1, math.ceil(error.retry_after_seconds / 60))
        wait_hours, remaining_minutes = divmod(wait_minutes, 60)
        wait_estimate = (
            f"{wait_hours}h {remaining_minutes}m"
            if wait_hours
            else f"{remaining_minutes} minutes"
        )
        return (
            "⚠️ The Gemini daily quota for this model is exhausted. "
            f"Google estimates it will reset in about {wait_estimate}. "
            "You can increase the quota or enable billing in Google AI Studio."
        )
    return (
        "⚠️ The Gemini daily quota for this model is exhausted. "
        "Please check your Google AI Studio quota or billing."
    )


async def send_result(status_msg, update, context, result: str):
    """Edit the status message with a result and send any remaining chunks."""
    chunks = split_telegram_text(result)
    if not chunks:
        await status_msg.edit_text("The model returned an empty response.", parse_mode=None)
        return

    await status_msg.edit_text(chunks[0], parse_mode=None)
    for chunk in chunks[1:]:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=chunk,
            parse_mode=None,
        )


async def execute_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE, mode_key: str):
    """Run a selected mode and show its result as plain text."""
    strategy = MODES.get(mode_key)
    if not strategy:
        return

    if not context.user_data.get("cv_text") or not context.user_data.get("vacancy_text"):
        await send_text(update, context, "⚠️ Please, load your CV and job description at first. Press /start.")
        return

    if getattr(strategy, "image_filename", None):
        await send_photo(update, context, strategy.image_filename)

    status_msg = await send_text(update, context, "🤖 <i>AI makes analysis of your data and generates resonse. Please hold a moment to get resonse...</i>")

    try:
        result = await strategy.execute(update, context)
    except Exception as e:
        print(f"Error while executing {mode_key}: {e}")
        await status_msg.edit_text(
            f"⚠️ Got an error during processing: {e}",
            parse_mode=None,
        )
        return

    context.user_data["step"] = "AWAITING_ADJUSTMENT"
    context.user_data["last_mode"] = mode_key
    context.user_data["last_result"] = result
    context.user_data["mode_adjustments"] = []
    await send_result(status_msg, update, context, result)
    await send_mode_actions(update, context, mode_key)


async def download_tailored_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send the tailored resume PDF after a resume audit."""
    strategy = MODES["review"]
    status_msg = await send_text(
        update,
        context,
        "🤖 Preparing your tailored resume PDF. Please wait...",
    )
    try:
        resume_text = await strategy.generate_tailored_resume(context)
        pdf_file = create_resume_pdf(resume_text)
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=pdf_file,
            filename="tailored_resume.pdf",
            caption="Your tailored resume is ready.",
        )
        await status_msg.edit_text("✅ Tailored resume PDF generated.", parse_mode=None)
    except GeminiQuotaExceeded as error:
        print(f"Gemini quota exhausted while generating tailored resume: {error}")
        await status_msg.edit_text(
            quota_exhausted_message(error) + " This request was not retried.",
            parse_mode=None,
        )
    except Exception as e:
        print(f"Error while generating tailored resume PDF: {e}")
        await status_msg.edit_text(
            "⚠️ I could not generate the tailored resume PDF. "
            "Please try again later or contact support if the problem continues.",
            parse_mode=None,
        )


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles selecting Inline-buttons."""
    query = update.callback_query
    await query.answer()

    action = query.data

    if action == "cmd_restart":
        await start(update, context)
        return

    if action == "action_retry_adjustment":
        await retry_saved_adjustments(update, context)
        return

    if action == "action_resume_pdf":
        if (
            not context.user_data.get("cv_text")
            or not context.user_data.get("vacancy_text")
        ):
            await send_text(update, context, "⚠️ Please load your CV and job description first. Press /start.")
            return
        if context.user_data.get("last_mode") != "review":
            await send_text(update, context, "Please run the resume audit before generating its tailored PDF.")
            return
        await download_tailored_resume(update, context)
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
    app.add_handler(
        CallbackQueryHandler(
            handle_callback_query,
            pattern="^(mode_|cmd_restart|action_)",
        )
    )
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_user_input))

    print("Bot is up and running with stateful architecture...")
    app.run_polling()


if __name__ == "__main__":
    main()