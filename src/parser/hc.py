from dataclasses import dataclass, field
from ..models.package import Package
from ..models.truck import Truck
from ..types.dimension import Dimension
from ..types.orientation import Orientation
from .helper import parse_int, parse_trucks, read_lines

# Deklarasi tipe jenis HC
HC_TYPES = {"HC_STEEPEST", "HC_SIDEWAYS", "HC_STOCHASTIC", "HC_RESTART"}

# Parameter unik untuk Steepest Ascent
@dataclass
class SteepestParams:
    num_cand: int = 50

# Parameter unik untuk Sideways HC
@dataclass
class SidewaysParams:
    num_cand: int = 50
    max_side: int = 100

# Parameter unik untuk Stochastic HC
@dataclass
class StochasticParams:
    nmax: int = 1000

# Parameter unik untuk Random Restart
@dataclass
class RestartParams:
    max_restart: int = 10
    num_cand: int = 50

# Parameter general untuk seluruh HC
@dataclass
class ProblemHC:
    hc_type: str
    truck: Truck
    packages: list[Package]
    params: SteepestParams | SidewaysParams | StochasticParams | RestartParams
    trucks: list[Truck] = field(default_factory=list)

# === Format file input HC ===
#
# HC_STEEPEST | HC_SIDEWAYS | HC_STOCHASTIC | HC_RESTART
# <W> <L> <H> <capacity> (1 atau beberapa baris untuk multi-truk)
# <m>
# <w> <l> <h> <weight> <value> [fragile] [eta] (sebanyak m baris)
# [parameter opsional]
#
# Urutan parameter opsional mengikuti jenis HC:
# - HC_STEEPEST  : [num_cand]
# - HC_SIDEWAYS  : [num_cand] [max_side]
# - HC_STOCHASTIC: [nmax]
# - HC_RESTART   : [max_restart] [num_cand]
#

# Parser utama Hill Climbing
def parse_hc(path: str) -> ProblemHC:
    lines = read_lines(path)

    # Memastikan minimal line terpenuhi, dan jenis HC dikenali
    if len(lines) < 3:
        raise ValueError("File terlalu pendek: minimal 3 baris (tipe, truk, m).")

    no0, hc_type = lines[0]
    hc_type = hc_type.strip().upper()
    if hc_type not in HC_TYPES:
        raise ValueError(f"Baris {no0}: tipe HC tidak dikenal '{hc_type}'. " f"Pilihan: {', '.join(sorted(HC_TYPES))}")

    # Membaca satu atau beberapa baris truk
    trucks, next_idx = parse_trucks(lines, 1)
    truck = trucks[0]

    if next_idx >= len(lines):
        raise ValueError("File tidak memiliki baris jumlah paket m setelah daftar truk.")

    # Memastikan jumlah paket sesuai
    no2, text2 = lines[next_idx]
    m = parse_int(text2, no2, "m")
    if m <= 0:
        raise ValueError(f"Baris {no2}: jumlah paket m harus > 0.")

    # Memastikan terdapat m baris yang sesuai
    pkg_start = next_idx + 1
    pkg_lines = lines[pkg_start : pkg_start + m]
    if len(pkg_lines) < m:
        raise ValueError(f"Butuh {m} baris paket, tetapi hanya tersedia {len(pkg_lines)}.")

    packages: list[Package] = []
    for i, (no, text) in enumerate(pkg_lines, 1):
        parts = text.split()
        if not (5 <= len(parts) <= 7):
            raise ValueError(f"Baris {no}: paket ke-{i} butuh 5–7 kolom " f"'w l h weight value [fragile] [eta]', dapat {len(parts)}.")
        nums = [parse_int(p, no, f"paket[{i}]") for p in parts]
        nums += [0] * (7 - len(nums))
        pw, pl, ph, weight, value, fragile, eta = nums

        if min(pw, pl, ph) <= 0:
            raise ValueError(f"Baris {no}: w, l, h paket ke-{i} harus > 0.")
        if min(weight, value, eta) < 0:
            raise ValueError(f"Baris {no}: weight/value/eta paket ke-{i} tidak boleh negatif.")

        packages.append(Package(
            id=f"p{i}",
            dimension=Dimension(pw, pl, ph),
            orientation=Orientation(("w", "l", "h")),
            value=value,
            weight=weight,
            is_fragile=bool(fragile),
            eta=eta,
        ))

    # Parse param
    rest = lines[pkg_start + m :]
    params = parse_params(hc_type, rest)

    return ProblemHC(hc_type=hc_type, truck=truck, packages=packages, params=params, trucks=trucks)


# Urutan parameter opsional di baris terakhir, disesuaikan dengan jenis HC, memakai default param jika tidak ada
PARAM_ORDER = {
    "HC_STEEPEST": ("num_cand",),
    "HC_SIDEWAYS": ("num_cand", "max_side"),
    "HC_STOCHASTIC": ("nmax",),
    "HC_RESTART": ("max_restart", "num_cand"),
}
PARAM_CLASSES = {
    "HC_STEEPEST": SteepestParams,
    "HC_SIDEWAYS": SidewaysParams,
    "HC_STOCHASTIC": StochasticParams,
    "HC_RESTART": RestartParams,
}

# Parser parameter untuk parsing tiap jenis pendekatan HC
def parse_params(hc_type: str, rest: list[tuple[int, str]]) -> SteepestParams | SidewaysParams | StochasticParams | RestartParams:
    parsers = {
        "HC_STEEPEST": parse_steepest_params,
        "HC_SIDEWAYS": parse_sideways_params,
        "HC_STOCHASTIC": parse_stochastic_params,
        "HC_RESTART": parse_restart_params,
    }
    try:
        return parsers[hc_type](rest)
    except KeyError:
        raise ValueError(f"Tipe HC tidak dikenal: '{hc_type}'.") from None

# Parser generik untuk parameter posisional HC
def parse_hc_params(hc_type: str, rest: list[tuple[int, str]]) -> SteepestParams | SidewaysParams | StochasticParams | RestartParams:
    names = PARAM_ORDER[hc_type]
    param_class = PARAM_CLASSES[hc_type]

    if not rest:
        return param_class()

    if len(rest) > 1:
        raise ValueError(
            f"Baris {rest[1][0]}: baris berlebih untuk {hc_type}. "
            f"Parameter cukup 1 baris: {' '.join(f'[{name}]' for name in names)}."
        )

    no, text = rest[0]
    parts = text.split()
    if len(parts) > len(names):
        raise ValueError(
            f"Baris {no}: {hc_type} menerima maksimal {len(names)} parameter "
            f"({', '.join(names)}), dapat {len(parts)}."
        )

    values = {}
    for token, name in zip(parts, names):
        value = parse_int(token, no, name)
        if value <= 0:
            raise ValueError(f"Baris {no}: {name} harus > 0.")
        values[name] = value

    return param_class(**values)

# Parser untuk steepest param ascent
def parse_steepest_params(rest: list[tuple[int, str]]) -> SteepestParams:
    return parse_hc_params("HC_STEEPEST", rest)

# Parser untuk sideways param move
def parse_sideways_params(rest: list[tuple[int, str]]) -> SidewaysParams:
    return parse_hc_params("HC_SIDEWAYS", rest)

# Parser untuk stochastic param HC
def parse_stochastic_params(rest: list[tuple[int, str]]) -> StochasticParams:
    return parse_hc_params("HC_STOCHASTIC", rest)

# Parser untuk random param restart
def parse_restart_params(rest: list[tuple[int, str]]) -> RestartParams:
    return parse_hc_params("HC_RESTART", rest)
