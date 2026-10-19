from dataclasses import dataclass, field
from ..models.package import Package
from ..models.truck import Truck
from ..types.dimension import Dimension
from ..types.orientation import Orientation
from .helper import parse_float, parse_int, parse_trucks, read_lines

@dataclass
class SAParams:
    t_start: float = 100.0
    alpha: float = 0.95
    t_min: float = 1e-2

@dataclass
class ProblemSA:
    truck: Truck
    packages: list[Package]
    params: SAParams
    trucks: list[Truck] = field(default_factory=list)

# === Format file SA ===
# SA
# <W> <L> <H> <capacity> (1 atau beberapa baris untuk multi-truk)
# <n>
# <w> <l> <h> <weight> <value> [fragile] [eta]   (sebanyak n baris)
# <t_start> <alpha> <t_min>   (opsional, 1 baris)

def parse_sa(path: str) -> ProblemSA:
    lines = read_lines(path)
    if len(lines) < 3 or lines[0][1] != "SA":
        raise ValueError("Baris pertama harus 'SA', lalu baris truk dan n")

    # Membaca satu atau beberapa baris truk
    trucks, next_idx = parse_trucks(lines, 1)
    truck = trucks[0]

    if next_idx >= len(lines):
        raise ValueError("File tidak memiliki baris jumlah paket n setelah daftar truk")

    # n
    no, text = lines[next_idx]
    n = parse_int(text, no, "n")
    if n <= 0:
        raise ValueError(f"Baris {no}: n harus > 0")

    # Paket
    pkg_start = next_idx + 1
    pkg_lines = lines[pkg_start : pkg_start + n]
    if len(pkg_lines) < n:
        raise ValueError(f"Butuh {n} baris paket, dapat {len(pkg_lines)}")

    packages = []
    for i, (no, text) in enumerate(pkg_lines, 1):
        parts = text.split()
        if not 5 <= len(parts) <= 7:
            raise ValueError(f"Baris {no}: paket butuh 5-7 angka 'w l h weight value [fragile] [eta]'")
        
        nums = [parse_int(p, no, "paket") for p in parts]
        nums += [0] * (7 - len(nums))  # fragile dan eta default 0
        pw, pl, ph, weight, value, fragile, eta = nums
        if min(pw, pl, ph) <= 0:
            raise ValueError(f"Baris {no}: w, l, h paket harus > 0")
        
        if min(weight, value, eta) < 0:
            raise ValueError(f"Baris {no}: weight/value/eta tidak boleh negatif")

        packages.append(Package(
            id=f"p{i}",
            dimension=Dimension(pw, pl, ph),
            orientation=Orientation(("w", "l", "h")),
            value=value,
            weight=weight,
            is_fragile=bool(fragile),
            eta=eta,
        ))

    # Params (opsional)
    params = SAParams()
    rest = lines[pkg_start + n :]

    if len(rest) > 1:
        raise ValueError(f"Baris {rest[1][0]}: baris berlebih, params cukup 1 baris")
    
    if rest:
        no, text = rest[0]
        parts = text.split()
        if len(parts) != 3:
            raise ValueError(f"Baris {no}: params butuh 3 angka 't_start alpha t_min'")
        
        t_start, alpha, t_min = [parse_float(p, no, name) for p, name in zip(parts, ("t_start", "alpha", "t_min"))]
        if t_start <= 0 or t_min <= 0:
            raise ValueError(f"Baris {no}: t_start dan t_min harus > 0")
        
        if not 0 < alpha < 1:
            raise ValueError(f"Baris {no}: alpha harus 0 < alpha < 1")
        
        params = SAParams(t_start, alpha, t_min)

    return ProblemSA(truck=truck, packages=packages, params=params, trucks=trucks)