from modes.base import BotMode
from util import send_photo, send_text, extract_text_from_file

class ResumeSummaryMode(BotMode):
    prompt_filename = "resume_summary.txt"
    image_filename = "AI_CV_Summary.png"