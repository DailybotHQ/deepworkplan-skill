import unittest
from src.client import total_of

class ClientUnitTest(unittest.TestCase):
    def test_total_with_mocked_transport(self):
        fake = lambda payload: {"total": 6}
        self.assertEqual(total_of([1, 2, 3], fake), 6)
