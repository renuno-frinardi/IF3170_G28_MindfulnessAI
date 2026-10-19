"""Definisi objective function yang dapat dipilih saat eksperimen"""

# Import library
from dataclasses import dataclass
import math

# Objective default untuk pemanggilan biasa
DEFAULT_OBJECTIVE = "value"

# Info objetif
@dataclass(frozen=True)
class ObjectiveInfo:
    id: str
    label: str
    description: str

# Definisi statis objektif
OBJECTIVES = {
    "value": ObjectiveInfo(
        id="value",
        label="Nilai total",
        description="Total nilai seluruh paket yang dimuat ke dalam truk.",
    ),
    "eta_penalty": ObjectiveInfo(
        id="eta_penalty",
        label="Nilai Total - Penalti ETA",
        description=(
            "Total nilai paket dikurangi penalti ETA untuk paket yang bertumpuk "
            "langsung dengan urutan ETA terbalik."
        ),
    ),
}

# Validasi nama objective
def validate_objective(mode: str) -> str:
    if not isinstance(mode, str) or mode not in OBJECTIVES:
        pilihan = ", ".join(OBJECTIVES)
        raise ValueError(f"Objective tidak dikenal: '{mode}' (valid: {pilihan}).")
    return mode

# Label objective untuk metadata dan GUI
def objective_label(mode: str) -> str:
    return OBJECTIVES[validate_objective(mode)].label

# Cek overlap footprint x-y
def overlap_xy(lower, upper) -> bool:
    lx0, ly0, _, lx1, ly1, _ = lower
    ux0, uy0, _, ux1, uy1, _ = upper
    return max(lx0, ux0) < min(lx1, ux1) and max(ly0, uy0) < min(ly1, uy1)

# Hitung detail objective ETA, yakni Hanya pasangan yang benar-benar bertumpuk langsung (z atas == z bawah) dan memiliki footprint x-y yang overlap yang dihitung.
def eta_penalty_details(state) -> dict[str, float | int | str]:
    inside = [package for package in state.packages if package.is_inside]
    base_value = float(sum(package.value for package in inside))
    penalty_total = 0
    penalty_count = 0

    positions = [(package, package.get_position()) for package in inside]
    for lower_package, lower_pos in positions:
        if lower_pos is None:
            continue
        for upper_package, upper_pos in positions:
            if upper_package is lower_package or upper_pos is None:
                continue
            if upper_pos[2] != lower_pos[5]:
                continue
            if not overlap_xy(lower_pos, upper_pos):
                continue
            if upper_package.eta > lower_package.eta:
                penalty_total += upper_package.eta - lower_package.eta
                penalty_count += 1

    # Penalti default bernilai 100 (biar nendang) dan dikalikan secara faktorial berdasarkan banyak total penalti
    penalty = max(float(penalty_total * 100), 100)
    for i in range(1, penalty_count+1):
        penalty = penalty * i

    # Mengembalikan penalti ETA
    return {
        "base_value": base_value,
        "penalty_total": float(penalty_total),
        "penalty_count": penalty_count,
        "penalty": penalty,
        "value": base_value - penalty,
    }

# Menghitung selutuh detil fungsi objekttif
def objective_details(state, mode: str = DEFAULT_OBJECTIVE) -> dict[str, float | int | str]:
    mode = validate_objective(mode)
    if mode == "eta_penalty":
        details = eta_penalty_details(state)
        details["objective"] = mode
        return details

    base_value = float(sum(package.value for package in state.packages if package.is_inside))

    return {
        "base_value": base_value,
        "penalty_total": 0.0,
        "penalty_count": 0,
        "penalty": 0.0,
        "value": base_value,
        "objective": mode,
    }

# Menghitung nilai objektif untuk algoritma
def calculate_objective(state, mode: str = DEFAULT_OBJECTIVE) -> float:
    return float(objective_details(state, mode)["value"])
