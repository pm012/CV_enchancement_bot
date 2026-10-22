import unittest

from util import split_telegram_text


class TelegramTextTests(unittest.TestCase):
    def test_splits_long_text_without_exceeding_utf16_limit(self):
        text = ("Line one.\n" * 450) + ("😀" * 10)

        chunks = split_telegram_text(text, limit=1000)

        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(
            all(len(chunk.encode("utf-16-le")) // 2 <= 1000 for chunk in chunks)
        )

    def test_rejects_non_positive_limit(self):
        with self.assertRaises(ValueError):
            split_telegram_text("text", limit=0)


if __name__ == "__main__":
    unittest.main()
