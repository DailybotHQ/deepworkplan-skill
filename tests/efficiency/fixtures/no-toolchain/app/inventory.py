def in_stock(items: dict, sku: str) -> bool:
    return items.get(sku, 0) > 0
