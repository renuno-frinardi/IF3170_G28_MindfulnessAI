from dataclasses import dataclass
from ..types.dimension import Dimension
from ..types.orientation import Orientation

@dataclass
class Package:
    id: str
    dimension: Dimension
    orientation: Orientation
    value: int
    weight: int
    is_fragile: bool
    eta: int

    # atribut tambahan untuk posisi package dalam truk
    x: int | None = None
    y: int | None = None
    z: int | None = None
    is_inside: bool = False # true kalau dalam truk, false kalau diluar truk

    # mengembalikan x,y,z min dan maks
    def get_position(self) -> tuple[int, int, int, int, int, int] | None:
        if not self.is_inside or self.x is None or self.y is None or self.z is None:
            return None

        dim_w, dim_l, dim_h = self.dimension.get_dimensions(self.orientation.orientation)
        return (self.x, self.y, self.z, self.x + dim_w, self.y + dim_l, self.z + dim_h)