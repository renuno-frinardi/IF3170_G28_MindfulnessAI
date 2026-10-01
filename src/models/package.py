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