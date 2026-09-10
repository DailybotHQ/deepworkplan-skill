def handle(payload: dict) -> dict:
    return {"total": sum(payload.get("items", []))}
