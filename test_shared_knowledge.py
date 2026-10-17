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

    def test_venues_available(self):
        self.assertIn("Бронзовая лошадь", main.SHARED_VENUES)
        self.assertIn("СПРАВОЧНИК ПЛОЩАДОК", main.PROMPT)
        self.assertIn("Количество гостей НЕ определяет размер экрана", main.SHARED_VENUES)

    def test_telegram_override_last(self):
        self.assertIn("Общие правила о необходимости номера телефона для MAX не относятся к Telegram", main.PROMPT)
        self.assertIn("этот чат является", main.PROMPT)
        self.assertGreater(main.PROMPT.index("ПРИОРИТЕТ ПЛАТФОРМЫ TELEGRAM BUSINESS"),
                           main.PROMPT.index("ОБЩАЯ БАЗА ПРАВИЛ"))

    def test_wedding_known_facts_across_turns(self):
        history = [
            {"role": "client", "text": "На свадьбу в горпарке нужен звук экран и свет"},
            {"role": "assistant", "text": "Когда дата и сколько гостей?"},
            {"role": "client", "text": "На свадьбе просто видео и слайдшоу"},
        ]
        facts = main.dialogue_guidance("30 чел 22 июля", history)
        self.assertTrue(facts["known_wedding"])
        self.assertTrue(facts["known_guests"])
        self.assertTrue(facts["known_date"])

    def test_one_final_summary_and_human_handoff_instruction(self):
        self.assertIn("ОДИН РАЗ в конце сборки заявки", main.PROMPT)
        self.assertIn("Андрей видит эту переписку", main.PROMPT)
        self.assertIn("не начинай новый цикл уточнений", main.PROMPT)
        self.assertIn("не пересказывай заявку повторно", main.PROMPT)

    def test_work_business_redirection_is_untouched(self):
        self.assertIn("Валентин", main.WORK_GREETING)
        self.assertIn("Андрей Стехин", main.WORK_GREETING)
        self.assertIn("greet_work_once", main.handle_message.__code__.co_names)

if __name__=="__main__":
    unittest.main()
