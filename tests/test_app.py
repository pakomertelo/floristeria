import os, tempfile, unittest
from urllib.parse import urlencode

fd, path = tempfile.mkstemp(suffix='.sqlite')
os.close(fd)
os.environ['DATABASE_PATH'] = path
os.environ['SESSION_SECRET'] = 'test-secret'
os.environ['ADMIN_EMAIL'] = 'admin@test.local'
os.environ['ADMIN_PASSWORD'] = 'Admin123!'

from src.db import init_db, connect
from src.server import App

class FakeHandler(App):
    def __init__(self):
        self.headers = {}
        self.client_address = ('127.0.0.1', 12345)

class AppSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_seed_creates_business_and_products(self):
        with connect() as db:
            self.assertEqual(db.execute('SELECT name FROM business_info WHERE id=1').fetchone()['name'], 'Floristería Mi Lindo Jardín')
            self.assertGreaterEqual(db.execute('SELECT COUNT(*) c FROM products WHERE visible=1').fetchone()['c'], 1)

    def test_csrf_tokens_are_single_use(self):
        h = FakeHandler()
        token = h.new_csrf()
        self.assertTrue(h.check_csrf(token))
        self.assertFalse(h.check_csrf(token))

    def test_contact_message_validation_helpers(self):
        from src.utils import is_email, clean
        self.assertTrue(is_email('cliente@example.com'))
        self.assertFalse(is_email('cliente-example.com'))
        self.assertEqual(clean('  hola\x00  '), 'hola')

if __name__ == '__main__':
    unittest.main()
