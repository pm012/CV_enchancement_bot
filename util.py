import io
from pypdf import PdfReader
from docx import Document
from telegram import Update, BotCommand, BotCommandScopeChat, MenuButtonCommands
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

def extract_text_from_file(file_bytes: bytes, file_name: str) -> str:
    """Helper function to cleanly pull text from uploaded PDF or DOCX files"""
    text = ""
    if file_name.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            text += page.extract_text() + "\n"
    elif file_name.lower().endswith(".docx"):
        doc = Document(io.BytesIO(file_bytes))
        for para in doc.paragraphs:
            text += para.text + "\n"
    return text.strip()

async def send_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, parse_mode=ParseMode.HTML):
    """Sends conversational updates back down to the target chat stream using HTML formatting"""
    return await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=text, 
        parse_mode=parse_mode
    )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, commands: dict):
    command_list = [BotCommand(key, value) for key, value in commands.items()]
    await context.bot.set_my_commands(command_list, scope=BotCommandScopeChat(chat_id=update.effective_chat.id))
    await context.bot.set_chat_menu_button(menu_button=MenuButtonCommands(), chat_id=update.effective_chat.id)
