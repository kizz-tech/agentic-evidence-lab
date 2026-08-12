def price_after_discount(price: int, percent: int) -> int:
    percent = min(100, max(0, percent))
    return round(price * (100 - percent) / 100)
