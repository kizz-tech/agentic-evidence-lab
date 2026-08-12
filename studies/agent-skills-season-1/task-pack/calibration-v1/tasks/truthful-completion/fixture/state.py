def format_state(record: dict[str, str]) -> str:
    return f"ready:{record['id']}"
