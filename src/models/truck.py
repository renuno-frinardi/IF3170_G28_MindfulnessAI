from dataclasses import dataclass
from ..types.dimension import Dimension

@dataclass
class Truck:
    dimension: Dimension
    max_capacity: int