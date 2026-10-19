from dataclasses import dataclass
from .helper import read_lines
from .ga import ProblemGA, parse_ga
from .hc import ProblemHC, parse_hc
from .sa import ProblemSA, parse_sa

@dataclass
class Problem:
    algo: str # "SA" atau "GA" atau "HC"
    problem: ProblemSA | ProblemGA | ProblemHC

PARSERS = {
    "SA": parse_sa,
    "GA": parse_ga,
}

HC = "HC_"

def parse(path: str) -> Problem:
    lines = read_lines(path)
    if not lines:
        raise ValueError("File kosong")

    first = lines[0][1]
    if first in PARSERS:
        return Problem(first, PARSERS[first](path))
    if first.startswith(HC):
        return Problem("HC", parse_hc(path))
    raise ValueError(f"Algoritma tidak dikenal: '{first}' (valid: SA, GA, HC)")