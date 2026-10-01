from dataclasses import dataclass, field
from ..types.dimension import Dimension
from .package import Package
from .truck import Truck

@dataclass
class State:
    packages: list[Package]
    truck: Truck
    value : float = 0.0

    def evaluate(self) -> float:
        total_value = 0.0
        total_weight = 0.0
        for package in self.packages:
            if package.is_inside:
                if not self.truck.is_package_fit(package):
                    return -float('inf')
                
                total_value += package.value
                total_weight += package.weight

        if total_weight > self.truck.max_capacity:
            return -float('inf')
        
        self.value = total_value
        return self.value