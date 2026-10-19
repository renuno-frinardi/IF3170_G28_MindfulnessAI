from dataclasses import dataclass
from ..models.package import Package
from ..models.truck import Truck
from ..types.dimension import Dimension
from ..types.orientation import Orientation
from .helper import parse_int, read_lines

# === Format file input GA ===
# GA
# <W> <L> <H> <capacity>
# <pilihan> = 'jumlah_populasi' | 'banyak_iterasi'
# <n> = jumlah_populasi | banyak_iterasi
# <m> = jumlah_package
# <w> <l> <h> <weight> <value> [fragile] [eta]   (sebanyak m baris)
@dataclass
class ProblemGA:
    truck: Truck
    packages: list[Package]
    pilihan: str
    n: int

def parse_ga(path: str):
    lines = read_lines(path)

    if len(lines) < 3 or lines[0][1] != "GA":
        raise ValueError("Baris pertama harus 'GA', lalu baris truk dan n")

    # Baris Truk: W L H capacity
    no, text = lines[1]
    parts = text.split()
    if len(parts) != 4:
        raise ValueError(f"Baris {no}: baris truk butuh 4 angka 'W L H capacity'")
    
    w, l, h, cap = [parse_int(p, no, name) for p, name in zip(parts, ("W", "L", "H", "capacity"))]
    if min(w, l, h, cap) <= 0:
        raise ValueError(f"Baris {no}: W, L, H, capacity harus > 0")
    truck = Truck(Dimension(w, l, h), cap)

    # Pilihan dan n
    text = lines[2][1]
    if (text.startswith("jumlah_populasi")):
        pilihan = "jumlah_populasi"
        n = parse_int(lines[3][1], lines[3][0], "jumlah_populasi")
    elif (text.startswith("banyak_iterasi")):
        pilihan = "banyak_iterasi"
        n = parse_int(lines[3][1], lines[3][0], "banyak_iterasi")
    else:
        raise ValueError(f"Baris {lines[2][0]}: pilihan tidak valid. Harus 'jumlah_populasi' atau 'banyak_iterasi'")

    # m
    text = lines[4][1]
    m = parse_int(text, lines[4][0], "jumlah_package")
    if m <= 0:
        raise ValueError(f"Baris {lines[4][0]}: jumlah_package harus > 0")

    # Packages
    pkg_lines = lines[5:5 + m]
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

    return ProblemGA(truck=truck, packages=packages, pilihan=pilihan, n=n)

# === Format file Output GA ===
# === GA ===
# <W> <L> <H> <capacity>
# Durasi Pencarian: <duration>
# Banyak iterasi: <iterations>
# Plot Nilai Objective Function
# <Plot>

# == Percobaan 1 == 
# Banyak iterasi: <iterations>
# Jumlah Populasi: <population_size>
# State awal: <initial_state>
# State akhir: <final_state>
# Nilai Objective Function Akhir: <final_objective_value>

# === Percobaan 2 ===
# === Percobaan 3 ===
# ...
# === Percobaan 9 ===

def output_ga(path: str):
    pass