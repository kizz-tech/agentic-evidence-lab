def encode(text: str) -> bytes:
    payload = text.encode("utf-8")
    return bytes([len(text)]) + payload


def decode(data: bytes) -> str:
    size = data[0]
    return data[1 : 1 + size].decode("utf-8")
