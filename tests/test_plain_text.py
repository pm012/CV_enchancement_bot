import unittest

from util import to_plain_text


class PlainTextTests(unittest.TestCase):
    def test_removes_common_markdown_without_changing_email_underscores(self):
        result = to_plain_text(
            "## **MATCHES**\n"
            "- **Experienced** in `Python`\n"
            "1. user_name@example.com\n"
            "> *Good fit*"
        )

        self.assertEqual(
            result,
            "MATCHES\nExperienced in Python\nuser_name@example.com\nGood fit",
        )


if __name__ == "__main__":
    unittest.main()
