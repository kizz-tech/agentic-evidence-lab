from formatter import format_user


def welcome(given: str, family: str) -> str:
    return f"Welcome, {format_user(given, family)}"

