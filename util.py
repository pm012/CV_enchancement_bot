import io
import os
from pypdf import PdfReader
from docx import Document
from telegram import (
    Update,
    BotCommand,
    BotCommandScopeChat,
    MenuButtonCommands,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# Визначення кореневої директорії проєкту та папки ресурсів
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(BASE_DIR, "resources")


def extract_text_from_file(file_bytes: bytes, file_name: str) -> str:
    """Витягує текст із завантажених файлів PDF або DOCX."""
    text = ""
    file_name_lower = file_name.lower()

    try:
        if file_name_lower.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

        elif file_name_lower.endswith(".docx"):
            doc = Document(io.BytesIO(file_bytes))
            for para in doc.paragraphs:
                if para.text:
                    text += para.text + "\n"

    except Exception as e:
        print(f"Помилка під час зчитування файлу {file_name}: {e}")
        return ""

    return text.strip()


def load_resource_text(category: str, name: str) -> str:
    """Завантажує текстовий файл із папки resources.
    
    Приклад використання:
    - load_resource_text("prompts", "cover_letter.txt") -> resources/prompts/cover_letter.txt
    - load_resource_text("text", "welcome.txt") -> resources/text/welcome.txt
    """
    path = os.path.join(RESOURCES_DIR, category, name)
    if not os.path.exists(path):
        print(f"Попередження: файл ресурсу не знайдено за шляхом: {path}")
        return ""

    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


async def send_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    parse_mode=ParseMode.HTML,
    reply_markup=None,
) -> Message:
    """Універсальна функція для відправки текстових повідомлень."""
    chat_id = update.effective_chat.id
    return await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
    )


async def send_buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    buttons: dict,
    layout: tuple = (2, 2, 1),
) -> Message:
    """Відправляє повідомлення з Inline-кнопками.
    
    :param buttons: Словник вида {'callback_data': 'Текст кнопки'}
    :param layout: Кортеж з кількістю кнопок у кожному рядку (наприклад, (2, 2, 1))
    """
    keyboard = []
    keys = list(buttons.keys())
    idx = 0

    for row_size in layout:
        row = []
        for _ in range(row_size):
            if idx < len(keys):
                k = keys[idx]
                row.append(InlineKeyboardButton(buttons[k], callback_data=str(k)))
                idx += 1
        if row:
            keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query and update.callback_query.message:
        return await update.callback_query.message.reply_text(
            text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )
    else:
        return await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )


async def send_photo(
    update: Update, context: ContextTypes.DEFAULT_TYPE, filename: str
) -> Message | None:
    """Відправляє зображення з папки resources/images/."""
    path = os.path.join(RESOURCES_DIR, "images", filename)
    if not os.path.exists(path):
        print(f"Зображення не знайдено: {path}")
        return None

    with open(path, "rb") as photo:
        return await context.bot.send_photo(
            chat_id=update.effective_chat.id, photo=photo
        )


async def show_main_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, commands: dict
):
    """Реєструє список команд у кнопці 'Menu' в інтерфейсі Telegram."""
    command_list = [BotCommand(key, value) for key, value in commands.items()]
    await context.bot.set_my_commands(
        command_list, scope=BotCommandScopeChat(chat_id=update.effective_chat.id)
    )
    await context.bot.set_chat_menu_button(
        menu_button=MenuButtonCommands(), chat_id=update.effective_chat.id
    )