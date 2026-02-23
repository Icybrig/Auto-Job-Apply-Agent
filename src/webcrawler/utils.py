import re


def to_digit(str: str) -> int | None:
    str = str.upper()
    match = re.search(r"(\d+).*?(K?)", str)
    if match:
        num = match.group(1)
        has_k = match.group(2) == "K"
        num = num * 1000 if has_k else num
        return int(num)
    return None