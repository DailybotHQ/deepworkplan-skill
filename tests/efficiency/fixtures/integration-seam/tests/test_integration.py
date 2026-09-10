import unittest
from src.client import total_of
from src.server import handle

class SeamIntegrationTest(unittest.TestCase):
    def test_client_against_real_server(self):
        self.assertEqual(total_of([1, 2, 3], handle), 6)
