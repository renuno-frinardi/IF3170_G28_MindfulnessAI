from dataclasses import dataclass, field
from ..models.package import Package
from ..models.truck import Truck
from ..types.dimension import Dimension
from ..types.orientation import Orientation
from .helper import parse_int, parse_trucks, read_lines

# === Format file input GA ===
# GA
# <W> <L> <H> <capacity> (1 atau beberapa baris untuk multi-truk)
# <pilihan> = 'jumlah_populasi' | 'banyak_iterasi'
# <n> = jumlah_populasi | banyak_iterasi
# <m> = jumlah_package
# <w> <l> <h> <weight> <value> [fragile] [eta]   (sebanyak m baris)

# Data structure ProblemGA untuk menyimpan data input Genetic Algorithm
@dataclass
class ProblemGA:
    truck: Truck
    packages: list[Package]
    pilihan: str
    n: int
    trucks: list[Truck] = field(default_factory=list)

# Parser file input ke bentuk problemGA
def parse_ga(path: str):
    lines = read_lines(path)

    if len(lines) < 3 or lines[0][1] != "GA":
        raise ValueError("Baris pertama harus 'GA', lalu baris truk dan n")

    # Membaca satu atau beberapa baris truk
    trucks, next_idx = parse_trucks(lines, 1)
    truck = trucks[0]

    if next_idx + 2 >= len(lines):
        raise ValueError("Input GA membutuhkan data truk, mode, nilai kontrol, dan jumlah paket")

    # Pilihan dan n
    text = lines[next_idx][1]
    if (text.startswith("jumlah_populasi")):
        pilihan = "jumlah_populasi"
        n = parse_int(lines[next_idx + 1][1], lines[next_idx + 1][0], "jumlah_populasi")
    elif (text.startswith("banyak_iterasi")):
        pilihan = "banyak_iterasi"
        n = parse_int(lines[next_idx + 1][1], lines[next_idx + 1][0], "banyak_iterasi")
    else:
        raise ValueError(f"Baris {lines[next_idx][0]}: pilihan tidak valid. Harus 'jumlah_populasi' atau 'banyak_iterasi'")

    # m
    m_idx = next_idx + 2
    text = lines[m_idx][1]
    m = parse_int(text, lines[m_idx][0], "jumlah_package")
    if m <= 0:
        raise ValueError(f"Baris {lines[m_idx][0]}: jumlah_package harus > 0")

    # Packages
    pkg_start = m_idx + 1
    pkg_lines = lines[pkg_start : pkg_start + m]
    if len(pkg_lines) < m:
        raise ValueError(f"Butuh {m} baris paket, dapat {len(pkg_lines)}")

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

    return ProblemGA(truck=truck, packages=packages, pilihan=pilihan, n=n, trucks=trucks)