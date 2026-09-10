import unittest
from src.greeter import greet

class T(unittest.TestCase):
    def test(self):
        self.assertEqual(greet('A'), 'Hello, A!')
