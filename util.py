import io
import os
from pypdf import PdfReader
from docx import Document
from telegram import Update, BotCommand, BotCommandScopeChat, MenuButtonCommands, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Message
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

async def send_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, parse_mode=ParseMode.HTML, reply_markup=None) -> Message:
    """Sends conversational updates back down to the target chat stream using HTML formatting"""
    chat_id = update.effective_chat.id
    return await context.bot.send_message(
        chat_id=chat_id, 
        text=text, 
        parse_mode=parse_mode,
        reply_markup=reply_markup
    )

async def send_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, buttons: dict) -> Message:
    """Sends a message equipped with layout-optimized inline action buttons"""
    keyboard = []
    for callback_data, button_label in buttons.items():
        keyboard.append([InlineKeyboardButton(button_label, callback_data=callback_data)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    return await send_text(update, context, text, reply_markup=reply_markup)

async def send_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, filename: str) -> Message:
    """Loads a graphical asset out of the resources/images path directory and transmits it"""
    path = os.path.join("resources", "images", filename)
    with open(path, "rb") as photo:
        return await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, commands: dict):
    command_list = [BotCommand(key, value) for key, value in commands.items()]
    await context.bot.set_my_commands(command_list, scope=BotCommandScopeChat(chat_id=update.effective_chat.id))
    await context.bot.set_chat_menu_button(menu_button=MenuButtonCommands(), chat_id=update.effective_chat.id)
