from dataclasses import dataclass
from ..types.dimension import Dimension
from .package import Package

@dataclass
class Truck:
    dimension: Dimension
    max_capacity: int

    # mengecek apakah paket berada dalam truk
    def is_in_truck(self, package: Package) -> bool:
        pos = package.get_position()
        if pos is None:
            return False

        x_min, y_min, z_min, x_max, y_max, z_max = pos
        return (
            0 <= x_min and x_max <= self.dimension.w and
            0 <= y_min and y_max <= self.dimension.l and
            0 <= z_min and z_max <= self.dimension.h
        )