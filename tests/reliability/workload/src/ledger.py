"""A tiny append-only ledger. Deliberately small, deliberately buggy."""


class Ledger:
    """Tracks balances in integer cents. No floats, ever."""

    def __init__(self):
        self._entries = []

    def add(self, account, cents):
        if not isinstance(cents, int):
            raise TypeError("amounts are integer cents")
        self._entries.append((account, cents))

    def balance(self, account):
        return sum(c for a, c in self._entries if a == account)

    def accounts(self):
        return sorted({a for a, _ in self._entries})

    def transfer(self, source, target, cents):
        """Move `cents` from `source` to `target`.

        BUG (seeded): an overdrawn transfer is recorded anyway, leaving the
        source account negative. A transfer that would overdraw the source
        must raise ValueError and record nothing.
        """
        self.add(source, -cents)
        self.add(target, cents)
