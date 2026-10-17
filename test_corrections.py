import os
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault("TELEGRAM_BOT_TOKEN","fake-token")
os.environ.setdefault("OPENAI_API_KEY","sk-test")
os.environ["DB_PATH"]=tempfile.mktemp(suffix=".db")
import main

class Corrections(unittest.TestCase):
    def test_venue_hall_date_city_and_format(self):
        key = "test:corrected"
        initial={k:"" for k in main.FIELDS}
        initial.update(event_type="свадьба", date="34 сентября", venue="Загарро", equipment="экран")
        main.apply_project(key, {"project_action":"new","project_id":0,"changes":initial}, [])
        _,_,projects=main.load_chat(key)
        self.assertEqual(len(projects),1)
        changes={k:"" for k in main.FIELDS}
        changes.update(date="23",venue="зал Грин",city="Загарро",guests="30",equipment="свет, звук, экран")
        main.apply_project(key, {"project_action":"update","project_id":projects[0]["id"],"changes":changes},projects)
        _,_,updated=main.load_chat(key)
        project=updated[0]
        self.assertEqual(project["date"],"23 сентября")
        self.assertEqual(project["venue"],"Загарро, зал Грин")
        self.assertEqual(project["city"],"")
        response=main.summary_reply(project)
        self.assertIn("\n• Площадка:",response)
        self.assertNotIn("\\n",response)
        self.assertNotIn("Город: Загарро",response)

if __name__=="__main__":unittest.main()
