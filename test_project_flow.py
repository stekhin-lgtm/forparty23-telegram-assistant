import os
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "fake-test-token")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-placeholder")
os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")
import main

class ProjectFlowTests(unittest.TestCase):
    def test_wedding_handoff_once(self):
        key="business:example-wedding"
        sent=[]
        entries=[
            ("На свадьбу в горпарке нужен звук экран и свет", "new", 0,
             {"event_type":"свадьба","venue":"Горпарк","equipment":"звук, экран, свет"}),
            ("Это свадьба, просто видео и слайдшоу", "update", 1,
             {"notes":"видео и слайд-шоу"}),
            ("30 чел 22 июля", "update", 1,
             {"guests":"30","date":"22 июля"})
        ]
        def fake_routing(text, history, projects):
            _,action,pid,changes=next(item for item in entries if item[0]==text)
            return {"project_action":action,"project_id":(projects[0]["id"] if action=="update" else 0),
                    "changes":{k:changes.get(k,"") for k in main.FIELDS}}
        with patch.object(main, "route_and_extract", side_effect=fake_routing), \
             patch.object(main, "make_reply", return_value={"reply":"Когда дата и сколько гостей?"}), \
             patch.object(main, "send", side_effect=lambda cid,reply,bid:sent.append(reply)):
            for text,_,_,_ in entries:
                main.client_message({"chat":{"id":"example-wedding"},"from":{"id":"client"},"text":text}, "business", "owner")
            self.assertEqual(len(sent),3)
            self.assertIn("Данные для предварительного расчёта собраны",sent[-1])
            self.assertIn("22 июля",sent[-1])
            self.assertIn("Горпарк",sent[-1])
            self.assertNotIn("Когда дата",sent[-1])
            main.client_message({"chat":{"id":"example-wedding"},"from":{"id":"client"},"text":"Спасибо"}, "business", "owner")
            self.assertEqual(sum("Данные для предварительного расчёта собраны" in x for x in sent),1)

    def test_separate_projects(self):
        self.assertTrue(main.project_ready({"event_type":"свадьба","date":"22 июля","venue":"Горпарк","equipment":"экран"}))
        self.assertFalse(main.project_ready({"event_type":"свадьба","date":"","venue":"Загарро","equipment":"свет"}))

if __name__=="__main__":unittest.main()
