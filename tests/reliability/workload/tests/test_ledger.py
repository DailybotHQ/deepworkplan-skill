import unittest

from src.ledger import Ledger


class LedgerTest(unittest.TestCase):
    def test_balance_sums_entries(self):
        ledger = Ledger()
        ledger.add("cash", 500)
        ledger.add("cash", -200)
        self.assertEqual(ledger.balance("cash"), 300)

    def test_rejects_non_integer_amounts(self):
        ledger = Ledger()
        with self.assertRaises(TypeError):
            ledger.add("cash", 1.5)

    def test_accounts_are_sorted_and_unique(self):
        ledger = Ledger()
        ledger.add("b", 1)
        ledger.add("a", 1)
        ledger.add("b", 1)
        self.assertEqual(ledger.accounts(), ["a", "b"])

    def test_transfer_moves_money(self):
        ledger = Ledger()
        ledger.add("cash", 1000)
        ledger.transfer("cash", "savings", 400)
        self.assertEqual(ledger.balance("cash"), 600)
        self.assertEqual(ledger.balance("savings"), 400)


if __name__ == "__main__":
    unittest.main()
