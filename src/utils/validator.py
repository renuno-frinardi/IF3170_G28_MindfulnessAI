from typing import List
from ..models.package import Package

def overlap(p1: Package, p2: Package) -> bool:
    pos1 = p1.get_position()
    pos2 = p2.get_position()

    if not pos1 or not pos2:
        return False

    x1_min, y1_min, z1_min, x1_max, y1_max, z1_max = pos1
    x2_min, y2_min, z2_min, x2_max, y2_max, z2_max = pos2

    return not (
        x1_max <= x2_min or x2_max <= x1_min or
        y1_max <= y2_min or y2_max <= y1_min or
        z1_max <= z2_min or z2_max <= z1_min
    )

# mengecek semua paket apakah ada yang tumpang tindih
def check_all_overlap(packages: List[Package]) -> bool:
    for i in range(len(packages)):
        for j in range(i + 1, len(packages)):
            if overlap(packages[i], packages[j]):
                return True
    return False

# mengecek apakah ada paket fragile yang menopang paket lain
def check_support_fragile(packages: List[Package]) -> bool:
    inside_pkg = [p for p in packages if p.is_inside]

    for pkg in inside_pkg:
        pos = pkg.get_position()
        if not pos:
            continue
        x_min, y_min, z_min, x_max, y_max, z_max = pos

        # paket langsung di atas lantai truk
        if z_min == 0:
            continue

        # mengecek apakah ada paket lain yang menumpuk di atas paket other
        supported = False
        for other in packages:
            if other.id == pkg.id:
                continue

            other_pos = other.get_position()
            if not other_pos:
                continue

            ox_min, oy_min, oz_min, ox_max, oy_max, oz_max = other_pos

            if oz_max == z_min:
                # mengecek apakah ada irisan area pada bidang alas
                overlap_x = max(ox_min, x_min) < min(ox_max, x_max)
                overlap_y = max(oy_min, y_min) < min(oy_max, y_max)

                if overlap_x and overlap_y:
                    # paket fragile tidak boleh menopang paket lain
                    if other.is_fragile:
                        return False
                    
                    supported = True
                    break

        if not supported:
            return False
            
    return True