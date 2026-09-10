import json, pathlib

def max_items() -> int:
    cfg = json.loads((pathlib.Path(__file__).parent.parent / "config" / "limits.json").read_text())
    return int(cfg["max_items"])
