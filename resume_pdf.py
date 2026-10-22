import io
import os
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def create_resume_pdf(resume_text: str) -> io.BytesIO:
    """Render plain-text resume content into a downloadable, Unicode PDF."""
    if not resume_text.strip():
        raise ValueError("Cannot create a PDF from an empty resume.")

    font_name = "ResumeFont"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        font_candidates = (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            os.path.join(os.path.dirname(reportlab.__file__), "fonts", "Vera.ttf"),
        )
        font_path = next(
            (path for path in font_candidates if os.path.isfile(path)),
            None,
        )
        if font_path is None:
            raise FileNotFoundError("No supported TrueType font was found for PDF export.")
        pdfmetrics.registerFont(TTFont(font_name, font_path))
    font = pdfmetrics.getFont(font_name)
    if any(
        not character.isspace() and ord(character) not in font.face.charToGlyph
        for character in resume_text
    ):
        raise ValueError("The available PDF font cannot render all resume characters.")

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=9.5,
        leading=13,
        spaceAfter=4,
        alignment=TA_LEFT,
    )
    heading_style = ParagraphStyle(
        "ResumeHeading",
        parent=body_style,
        fontSize=11,
        leading=14,
        spaceBefore=9,
        spaceAfter=4,
        textColor=colors.HexColor("#1F3A5F"),
    )
    name_style = ParagraphStyle(
        "ResumeName",
        parent=body_style,
        fontSize=18,
        leading=22,
        spaceAfter=8,
        textColor=colors.HexColor("#1F3A5F"),
    )

    story = []
    first_line = True
    for line in resume_text.splitlines():
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue

        escaped_line = escape(line)
        if first_line:
            style = name_style
            first_line = False
        elif line.isupper() and len(line) <= 60:
            style = heading_style
        else:
            style = body_style
        story.append(Paragraph(escaped_line, style))

    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=LETTER,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Tailored Resume",
        author="AI Career Assistant",
    )
    document.build(story)
    output.seek(0)
    return output
