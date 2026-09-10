def total_of(items, transport):
    return transport({"items": list(items)})["total"]
