def with_tax(amount: float, rate: float = 0.19) -> float:
    return round(amount * (1 + rate), 2)
