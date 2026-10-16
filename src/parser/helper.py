Line = tuple[int, str]  # nomor dan isi baris

def read_lines(path: str) -> list[Line]:
    out = []
    with open(path, encoding="utf-8") as f:
        for no, raw in enumerate(f, 1):
            s = raw.strip()
            if s:
                out.append((no, s))
    return out

def parse_int(token: str, line: int, name: str) -> int:
    try:
        return int(token)
    except ValueError:
        raise ValueError(f"Baris {line}: {name} harus integer, dapat '{token}'")

def parse_float(token: str, line: int, name: str) -> float:
    try:
        return float(token)
    except ValueError:
        raise ValueError(f"Baris {line}: {name} harus angka, dapat '{token}'")