from ..models.truck import Truck
from ..types.dimension import Dimension

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

def parse_trucks(lines: list[Line], start_idx: int = 1) -> tuple[list[Truck], int]:
    # Membaca satu atau beberapa baris truk (<W> <L> <H> <capacity>) secara berurutan 
    trucks: list[Truck] = []
    idx = start_idx
    while idx < len(lines):
        no, text = lines[idx]
        parts = text.split()
        # Baris setelah daftar truk selalu memiliki 1 kolom (<m>, <n>, atau <pilihan> GA)
        if idx > start_idx and len(parts) == 1:
            break
        if len(parts) != 4:
            raise ValueError(f"Baris {no}: baris truk butuh 4 angka 'W L H capacity', dapat {len(parts)}.")
        w, l, h, cap = [parse_int(p, no, name) for p, name in zip(parts, ("W", "L", "H", "capacity"))]
        if min(w, l, h, cap) <= 0:
            raise ValueError(f"Baris {no}: W, L, H, capacity harus > 0.")
        trucks.append(Truck(Dimension(w, l, h), cap))
        idx += 1

    if not trucks:
        raise ValueError("Minimal dibutuhkan satu baris truk.")
    return trucks, idx