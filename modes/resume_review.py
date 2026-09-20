from modes.base import BotMode
from util import send_photo, send_text, extract_text_from_file

class ResumeReviewMode(BotMode):
    prompt_filename = "resume_review.txt"
    image_filename = "CV_improvement.jpeg"