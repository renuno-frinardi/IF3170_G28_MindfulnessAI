from dataclasses import dataclass
from .package import Package
from .truck import Truck
from ..objective import DEFAULT_OBJECTIVE, objective_details
from ..utils.validator import is_feasible

@dataclass
class State:
    packages: list[Package]
    truck: Truck
    value : float = 0.0
    objective_mode: str = DEFAULT_OBJECTIVE

    def objective_value(self) -> float:
        return float(self.objective_details()["value"])

    def objective_details(self) -> dict[str, float | int | str]:
        return objective_details(self, self.objective_mode)

    def evaluate(self) -> float:
        # melanggar aturan
        if not is_feasible(self):
            self.value = -float('inf')
            return self.value

        self.value = self.objective_value()
        return self.value
