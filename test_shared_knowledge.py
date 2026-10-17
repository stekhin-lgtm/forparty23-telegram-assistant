"""Offline checks for shared knowledge setup and Telegram-specific overrides."""
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "fake-bot-token")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-placeholder")
os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")

import main

class SharedKnowledgeTests(unittest.TestCase):
    def test_shared_files_loaded(self):
        self.assertIn("Stekhin AI", main.SHARED_RULES)
        self.assertIn("STEKHIN AI", main.SHARED_KNOWLEDGE)

    def test_telegram_override_last(self):
        self.assertIn("Общие правила о необходимости номера телефона для MAX не относятся к Telegram", main.PROMPT)
        self.assertIn("этот чат является", main.PROMPT)
        self.assertGreater(main.PROMPT.index("ПРИОРИТЕТ ПЛАТФОРМЫ TELEGRAM BUSINESS"),
                           main.PROMPT.index("ОБЩАЯ БАЗА ПРАВИЛ"))

    def test_work_business_redirection_is_untouched(self):
        self.assertIn("Валентин", main.WORK_GREETING)
        self.assertIn("Андрей Стехин", main.WORK_GREETING)
        self.assertIn("greet_work_once", main.handle_message.__code__.co_names)

if __name__=="__main__":
    unittest.main()
