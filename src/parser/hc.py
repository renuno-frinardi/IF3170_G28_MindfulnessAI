from dataclasses import dataclass, field
from ..models.package import Package
from ..models.truck import Truck
from ..types.dimension import Dimension
from ..types.orientation import Orientation
from .helper import parse_int, read_lines

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

# === Format file input HC ===
#
# HC_STEEPEST | HC_SIDEWAYS | HC_STOCHASTIC | HC_RESTART
# <W> <L> <H> <capacity>
# <m>
# <w> <l> <h> <weight> <value> (sebanyak m baris)

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

    # Memastikan dimensi truk sesuai
    no1, text1 = lines[1]
    parts1 = text1.split()
    if len(parts1) != 4:
        raise ValueError(f"Baris {no1}: baris truk butuh 4 angka 'W L H capacity', " f"dapat {len(parts1)}.")
    w, l, h, cap = [parse_int(p, no1, name) for p, name in zip(parts1, ("W", "L", "H", "capacity"))]
    if min(w, l, h, cap) <= 0:
        raise ValueError(f"Baris {no1}: W, L, H, capacity harus > 0.")
    truck = Truck(Dimension(w, l, h), cap)

    # Memastikan jumlah paket sesuai
    no2, text2 = lines[2]
    m = parse_int(text2, no2, "m")
    if m <= 0:
        raise ValueError(f"Baris {no2}: jumlah paket m harus > 0.")

    # Memastikan terdapat m baris yang sesuai
    pkg_lines = lines[3 : 3 + m]
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
    rest = lines[3 + m :]
    params = parse_params(hc_type, rest)

    return ProblemHC(hc_type=hc_type, truck=truck, packages=packages, params=params)


# Parser parameter untuk parsing tiap jenis pendekatan HC
def parse_params(hc_type: str, rest: list[tuple[int, str]]) -> SteepestParams | SidewaysParams | StochasticParams | RestartParams:
    if hc_type == "HC_STEEPEST":
        return parse_steepest_params(rest)
    elif hc_type == "HC_SIDEWAYS":
        return parse_sideways_params(rest)
    elif hc_type == "HC_STOCHASTIC":
        return parse_stochastic_params(rest)
    else:
        return parse_restart_params(rest)

# Parser untuk steepest ascent
def parse_steepest_params(rest: list[tuple[int, str]]) -> SteepestParams:
    if not rest:
        return SteepestParams()

    if len(rest) > 1:
        raise ValueError(f"Baris {rest[1][0]}: baris berlebih untuk HC_STEEPEST. " f"Parameter cukup 1 baris: 'num_cand'.")

    no, text = rest[0]
    parts = text.split()
    if len(parts) != 1:
        raise ValueError(f"Baris {no}: HC_STEEPEST butuh 1 parameter 'num_cand', " f"dapat {len(parts)}.")
    num_cand = parse_int(parts[0], no, "num_cand")
    if num_cand <= 0:
        raise ValueError(f"Baris {no}: num_cand harus > 0.")
    return SteepestParams(num_cand=num_cand)

# Parser untuk sideways param
def parse_sideways_params(rest: list[tuple[int, str]]) -> SidewaysParams:
    if not rest:
        return SidewaysParams()

    if len(rest) > 1:
        raise ValueError(f"Baris {rest[1][0]}: baris berlebih untuk HC_SIDEWAYS. " f"Parameter cukup 1 baris: 'num_cand max_side'.")

    no, text = rest[0]
    parts = text.split()
    if len(parts) != 2:
        raise ValueError(f"Baris {no}: HC_SIDEWAYS butuh 2 parameter " f"'num_cand max_side', dapat {len(parts)}.")
    num_cand = parse_int(parts[0], no, "num_cand")
    max_side = parse_int(parts[1], no, "max_side")

    if num_cand <= 0:
        raise ValueError(f"Baris {no}: num_cand harus > 0.")
    if max_side <= 0:
        raise ValueError(f"Baris {no}: max_side harus > 0.")

    return SidewaysParams(num_cand=num_cand, max_side=max_side)

# Parser untuk stochastic param
def parse_stochastic_params(rest: list[tuple[int, str]]) -> StochasticParams:
    if not rest:
        return StochasticParams()

    if len(rest) > 1:
        raise ValueError(f"Baris {rest[1][0]}: baris berlebih untuk HC_STOCHASTIC. " f"Parameter cukup 1 baris: 'nmax'.")

    no, text = rest[0]
    parts = text.split()
    if len(parts) != 1:
        raise ValueError(f"Baris {no}: HC_STOCHASTIC butuh 1 parameter 'nmax', " f"dapat {len(parts)}.")
    nmax = parse_int(parts[0], no, "nmax")
    if nmax <= 0:
        raise ValueError(f"Baris {no}: nmax harus > 0.")
    return StochasticParams(nmax=nmax)

# Parser untuk random restart param
def parse_restart_params(rest: list[tuple[int, str]]) -> RestartParams:
    if not rest:
        return RestartParams()

    if len(rest) > 1:
        raise ValueError(f"Baris {rest[1][0]}: baris berlebih untuk HC_RESTART. " f"Parameter cukup 1 baris: 'max_restart num_cand'.")

    no, text = rest[0]
    parts = text.split()
    if len(parts) != 2:
        raise ValueError(f"Baris {no}: HC_RESTART butuh 2 parameter " f"'max_restart num_cand', dapat {len(parts)}.")
    max_restart = parse_int(parts[0], no, "max_restart")
    num_cand = parse_int(parts[1], no, "num_cand")

    if max_restart <= 0:
        raise ValueError(f"Baris {no}: max_restart harus > 0.")
    if num_cand <= 0:
        raise ValueError(f"Baris {no}: num_cand harus > 0.")

    return RestartParams(max_restart=max_restart, num_cand=num_cand)
