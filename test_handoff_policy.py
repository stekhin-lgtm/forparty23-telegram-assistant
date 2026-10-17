import pathlib
import unittest

class TestHandoffPolicy(unittest.TestCase):
    def test_shared_policy(self):
        root = pathlib.Path(__file__).resolve().parent
        policy = (root / 'handoff_policy.md').read_text(encoding='utf-8')
        self.assertIn('резюме', policy)
        self.assertIn('Технические решения', policy)
        self.assertIn('Telegram Business', policy)
        self.assertIn('MAX', policy)

if __name__ == '__main__':
    unittest.main()
