import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, CallbackQueryHandler
from telegram import ReplyKeyboardMarkup

from llm_genai import GeminiChatService
from util import show_main_menu, send_text, send_buttons, send_photo

from modes.cover_letter import CoverLetterMode
from modes.linkedin import LinkedInMode
from modes.resume_summary import ResumeSummaryMode
from modes.resume_review import ResumeReviewMode

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_TOKEN = os.getenv("GEMINI_API_KEY")

llm_service = GeminiChatService(token=GEMINI_TOKEN)

MODES = {
    "cover_letter": CoverLetterMode(llm_service),
    "linkedin": LinkedInMode(llm_service),
    "summary": ResumeSummaryMode(llm_service),
    "review": ResumeReviewMode(llm_service)
}

async def start(update, context):    
    context.user_data["current_mode"] = None
    
    welcome_text = (
        "<b>Welcome to your AI Career Assistant!</b>\n\n"
        "Select an option below to start polishing your career documents:"
    )
    
    # Coded unicode sequences replacing direct graphic emojis
    action_buttons = {
        "mode_cover_letter": "Create Cover Letter \uD83D\uDCDD",
        "mode_linkedin": "Optimize LinkedIn Profile \uD83D\uDCCA",
        "mode_summary": "Generate Resume Summary \uD83D\uDCCB",
        "mode_review": "Audit Resume vs Vacancy \uD83D\uDD0D"
    }
    
    menu_keyboard = [["Restart / Back to Main Menu \u21BB"]]
    reply_markup = ReplyKeyboardMarkup(menu_keyboard, resize_keyboard=True)
    
    # Send Graphic and Action Elements sequentially
    await send_photo(update, context, "AI-Resume-welcomescreen.png")
    await send_text(update, context, welcome_text, reply_markup=reply_markup)
    await send_buttons(update, context, "<b>Available Tools:</b>", action_buttons)
    
    await show_main_menu(update, context, {"start": "Main Menu / Help"})

async def handle_callback_query(update, context):
    query = update.callback_query
    await query.answer()
    
    chosen_mode = query.data.replace("mode_", "").strip()
    if chosen_mode in MODES:
        context.user_data["current_mode"] = chosen_mode
        # FIXED: Passing update (which contains the callback query information) and context correctly
        await MODES[chosen_mode].start(update, context) 

async def handle_user_input(update, context):
    user_text = update.message.text
    if user_text and user_text.startswith("Restart / Back to Main Menu"):
        await start(update, context)
        return

    active_mode_name = context.user_data.get("current_mode")
    if active_mode_name in MODES:
        await MODES[active_mode_name].handle_message(update, context)
    else:
        await send_text(update, context, "Please select an option from the menu or click an interactive tool.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback_query, pattern="^mode_"))
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_user_input))
    
    print("Asset loading structure operational. Running polling loop...")
    app.run_polling()

if __name__ == "__main__":
    main()
