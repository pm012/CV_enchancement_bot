import unittest

from pypdf import PdfReader

from resume_pdf import create_resume_pdf


class ResumePdfTests(unittest.TestCase):
    def test_creates_readable_pdf_with_resume_content(self):
        pdf_file = create_resume_pdf(
            "Alex Example\n"
            "PROFESSIONAL SUMMARY\n"
            "Experienced engineer with 10 years of experience.\n"
            "SKILLS\n"
            "Python & data systems"
        )

        reader = PdfReader(pdf_file)
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)

        self.assertEqual(len(reader.pages), 1)
        self.assertIn("Alex Example", extracted_text)
        self.assertIn("PROFESSIONAL SUMMARY", extracted_text)
        self.assertIn("Python & data systems", extracted_text)

    def test_rejects_empty_resume(self):
        with self.assertRaises(ValueError):
            create_resume_pdf(" \n ")

    def test_preserves_cyrillic_text(self):
        pdf_file = create_resume_pdf("Іван Петренко\nДОСВІД РОБОТИ")

        extracted_text = "\n".join(
            page.extract_text() or "" for page in PdfReader(pdf_file).pages
        )

        self.assertIn("Іван Петренко", extracted_text)
        self.assertIn("ДОСВІД РОБОТИ", extracted_text)


if __name__ == "__main__":
    unittest.main()
