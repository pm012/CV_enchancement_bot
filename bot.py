import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler

from llm_genai import GeminiChatService
from util import show_main_menu, send_text

# Import all strategy modules
from modes.cover_letter import CoverLetterMode
from modes.linkedin import LinkedInMode
from modes.resume_summary import ResumeSummaryMode  
from modes.resume_review import ResumeReviewMode    

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_TOKEN = os.getenv("GEMINI_API_KEY")

llm_service = GeminiChatService(token=GEMINI_TOKEN)

# Register the updated modes map
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
        "Use the menu command buttons to select a feature:\n"
        "/cover_letter — Tailored Cover Letter\n"
        "/linkedin — LinkedIn Profile Optimization\n"
        "/summary — Strategic Resume Summary\n"
        "/review — Critical ATS Resume Audit"
    )
    await send_text(update, context, welcome_text)
    await show_main_menu(update, context, {
        "start": "Show menu help",
        "cover_letter": "Create Cover Letter ",
        "linkedin": "Optimize LinkedIn Profile ",
        "summary": "Generate Resume Summary ",
        "review": "Audit Resume vs Vacancy ",
    })
async def route_command(update, context):
    command = update.message.text.replace("/", "").strip()
    if command in MODES:
        context.user_data["current_mode"] = command
        await MODES[command].start(update, context)

async def handle_user_input(update, context):
    active_mode_name = context.user_data.get("current_mode")
    if active_mode_name in MODES:
        await MODES[active_mode_name].handle_message(update, context)
    else:
        await send_text(update, context, "Please select an action from the menu command options first (e.g. /summary).")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    for mode_name in MODES.keys():
        app.add_handler(CommandHandler(mode_name, route_command))
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_user_input))
    
    print("Structural Career Application router initialized. Running live polling loop...")
    app.run_polling()

if __name__ == "__main__":
    main()
