import unittest
from unittest.mock import patch
import os, tempfile
os.environ["TELEGRAM_BOT_TOKEN"]="test"
os.environ["OPENAI_API_KEY"]="sk-test"
os.environ["DB_PATH"]=tempfile.mktemp(suffix=".db")
import main

class CityTests(unittest.TestCase):
    def test_given_city_is_not_reconfirmed(self):
        data={"reply":"Площадка Бронзовая Лошадь находится в Краснодаре, верно?","project_action":"none","project_id":0,"changes":{k:"" for k in main.FIELDS}}
        received=[]
        with patch.object(main,"make_reply",return_value=data), patch.object(main,"send",side_effect=lambda *a: received.append(a[1])):
            main.client_message({"chat":{"id":873543,"type":"private"},"from":{"id":873543},"text":"Да Лофт Бронзовая лошадь Краснодар"},None,"")
        self.assertTrue(received)
        self.assertNotIn("верно?",received[-1])
        self.assertIn("подобрать",received[-1])

if __name__ == "__main__": unittest.main()
