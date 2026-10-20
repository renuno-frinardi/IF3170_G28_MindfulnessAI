from ..models.package import Package

# cek dua paket overlap atau tidak
def overlap(p1: Package, p2: Package) -> bool:
    pos1 = p1.get_position()
    pos2 = p2.get_position()

    if pos1 is None or pos2 is None:
        return False

    x1_min, y1_min, z1_min, x1_max, y1_max, z1_max = pos1
    x2_min, y2_min, z2_min, x2_max, y2_max, z2_max = pos2

    return not (
        x1_max <= x2_min or x2_max <= x1_min or
        y1_max <= y2_min or y2_max <= y1_min or
        z1_max <= z2_min or z2_max <= z1_min
    )

# cek apakah state melanggar aturan atau tidak
def violations(state) -> list[str]:
    result = []
    packages = state.packages
    truck = state.truck

    inside = []
    for p in packages:
        if p.is_inside:
            inside.append(p)

    # aturan koordinat harus integer + aturan paket luar/dalam
    for p in packages:
        for v, var in ((p.x, "x"), (p.y, "y"), (p.z, "z")):
            if v is not None and type(v) is not int:
                result.append(p.id + ": koordinat " + var + " bukan integer")
        if not p.is_inside:
            if p.x is not None or p.y is not None or p.z is not None:
                result.append(p.id + ": di luar tapi masih punya koordinat")
        else:
            if p.x is None or p.y is None or p.z is None:
                result.append(p.id + ": di dalam tapi koordinat belum lengkap")

    # aturan keluar dari truck
    for p in inside:
        if not truck.is_in_truck(p):
            result.append(p.id + ": keluar dari truck")

    # aturan overlap
    for i in range(len(inside)):
        for j in range(i + 1, len(inside)):
            if overlap(inside[i], inside[j]):
                result.append(inside[i].id + " menumpuk " + inside[j].id)

    # aturan melayang
    for pkg in inside:
        pos = pkg.get_position()
        if pos is None:
            continue

        x_min, y_min, z_min, x_max, y_max, _ = pos
        if z_min == 0: # di lantai
            continue

        found = False
        for other in inside:
            if other.id == pkg.id: # paket yang sama
                continue

            opos = other.get_position()
            if opos is None:
                continue

            ox_min, oy_min, oz_min, ox_max, oy_max, oz_max = opos
            if oz_max == z_min:
                overlap_x = max(ox_min, x_min) < min(ox_max, x_max)
                overlap_y = max(oy_min, y_min) < min(oy_max, y_max)
                if overlap_x and overlap_y:
                    found = True
                    break

        if not found:
            result.append(pkg.id + ": melayang")

    # aturan paket fragile tidak boleh menopang paket lain
    for fragile in inside:
        if not fragile.is_fragile:
            continue

        fpos = fragile.get_position()
        if fpos is None:
            continue

        fx_min, fy_min, _, fx_max, fy_max, fz_max = fpos
        above = [] # paket di atas fragile
        for other in inside:
            if other.id == fragile.id:
                continue

            opos = other.get_position()
            if opos is None:
                continue

            ox_min, oy_min, oz_min, ox_max, oy_max, oz_max = opos
            if oz_min == fz_max:
                overlap_x = max(ox_min, fx_min) < min(ox_max, fx_max)
                overlap_y = max(oy_min, fy_min) < min(oy_max, fy_max)
                if overlap_x and overlap_y:
                    above.append(other.id)

        if above:
            result.append(fragile.id + " (fragile) menopang " + ",".join(sorted(above)))

    # aturan total berat > kapasitas
    total = 0
    for p in inside:
        total = total + p.weight
    if total > truck.max_capacity:
        result.append("Kelebihan berat: " + str(total) + " > " + str(truck.max_capacity))

    return result

def is_feasible(state):
    return len(violations(state)) == 0