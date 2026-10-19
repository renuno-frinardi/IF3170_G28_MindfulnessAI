from dataclasses import dataclass
from .package import Package
from .truck import Truck
from ..utils.validator import is_feasible

@dataclass
class State:
    packages: list[Package]
    truck: Truck
    value : float = 0.0

    def objective_value(self) -> float:
        return float(sum(p.value for p in self.packages if p.is_inside))

    def evaluate(self) -> float:
        # melanggar aturan
        if not is_feasible(self):
            self.value = -float('inf')
            return self.value

        self.value = self.objective_value()
        return self.value
