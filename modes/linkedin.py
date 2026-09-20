from modes.base import BotMode
from util import send_photo, send_text, extract_text_from_file

class LinkedInMode(BotMode):
    prompt_filename = "linkedin.txt"
    image_filename = "LinkedInSummary.png"
