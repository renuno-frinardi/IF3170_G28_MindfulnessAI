import math
import random
from dataclasses import asdict, dataclass, field
from .algorithms.genetic_algorithm.genetic_algorithm import genetic_algorithm
from .algorithms.hill_climbing.restart import random_restart_hill_climbing
from .algorithms.hill_climbing.sideways import sideways_move_hill_climbing
from .algorithms.hill_climbing.steepest_ascent import steepest_ascent_hill_climbing
from .algorithms.hill_climbing.stochastic import stochastic_hill_climbing
from .algorithms.simulated_annealing.simulated_annealing import simulated_annealing
from .models.state import State
from .objective import DEFAULT_OBJECTIVE, validate_objective
from .parser.main import Problem
from .utils.state_utils import random_initial_state

HC_ALGORITHMS = {
    "HC_STEEPEST": steepest_ascent_hill_climbing,
    "HC_SIDEWAYS": sideways_move_hill_climbing,
    "HC_STOCHASTIC": stochastic_hill_climbing,
    "HC_RESTART": random_restart_hill_climbing,
}

@dataclass
class SolveResult:
    algo: str
    init_state: State
    final_state: State
    final_value: float
    value_history: list[float | None]
    iterations: int
    duration: float
    extra: dict = field(default_factory=dict)

def clean(history) -> list[float | None]: # nilai -inf diubah jadi None
    return [None if (isinstance(v, float) and math.isinf(v) and v < 0) else v for v in history]

def solve(parsed: Problem, seed: int | None = None, objective_mode: str = DEFAULT_OBJECTIVE) -> SolveResult:
    objective_mode = validate_objective(objective_mode)
    if parsed.algo == "SA":
        return solve_sa(parsed.problem, seed, objective_mode)
    if parsed.algo == "GA":
        return solve_ga(parsed.problem, seed, objective_mode)
    if parsed.algo == "HC":
        return solve_hc(parsed.problem, seed, objective_mode)
    raise ValueError(f"Algoritma tidak dikenal: '{parsed.algo}'")

def solve_sa(problem, seed, objective_mode: str = DEFAULT_OBJECTIVE) -> SolveResult:
    rng = random.Random(seed)
    init = random_initial_state(problem.packages, problem.truck, seed=seed, objective_mode=objective_mode)
    res = simulated_annealing(init, rng, problem.params.t_start, problem.params.alpha, problem.params.t_min)

    history = res["history"]
    final = res["final"]
    return SolveResult(
        algo="SA",
        init_state=res["initial"],
        final_state=final,
        final_value=final.value,
        value_history=clean(history),
        iterations=len(history),
        duration=res["duration"],
        extra={
            "probs": res["probs"],
            "stuck": res["stuck"],
            "best_state": res["best"],
        },
    )

def solve_ga(problem, seed, objective_mode: str = DEFAULT_OBJECTIVE) -> SolveResult:
    res = genetic_algorithm(problem.packages, problem.truck, problem.pilihan, problem.n, seed=seed, objective_mode=objective_mode)
    results = res["results"]
    if not results:
        raise ValueError("GA tidak menghasilkan solusi")

    best = results[0]
    for result in results:
        if result["final_objective"] > best["final_objective"]:
            best = result
    history = best["objective_history"]["maximum"]
    return SolveResult(
        algo="GA",
        init_state=best["initial_state"],
        final_state=best["final_state"],
        final_value=best["final_objective"],
        value_history=clean(history),
        iterations=best["iterations"],
        duration=best["duration_seconds"],
        extra={
            "pilihan": res["pilihan"],
            "nilai_kontrol": res["nilai_kontrol"],
            "results": results,
            "average": best["objective_history"]["average"],
            "population_size": best["population_size"],
        },
    )

def solve_hc(problem, seed, objective_mode: str = DEFAULT_OBJECTIVE) -> SolveResult:
    hc_type = problem.hc_type
    if hc_type not in HC_ALGORITHMS:
        raise ValueError(f"Tipe HC tidak dikenal: '{hc_type}'")

    algo = HC_ALGORITHMS[hc_type]
    params = asdict(problem.params)

    if hc_type == "HC_RESTART":
        res = algo(problem.packages, problem.truck, **params, seed=seed, objective_mode=objective_mode)
    else:
        init = random_initial_state(problem.packages, problem.truck, seed=seed, objective_mode=objective_mode)
        res = algo(init, **params, seed=seed)

    extra = {}
    if "sideways_moves" in res:
        extra["sideways_moves"] = res["sideways_moves"]
    if "all_histories" in res:
        extra["all_histories"] = res["all_histories"]
        extra["iterations_per_restart"] = res["iterations_per_restart"]
        extra["total_restarts"] = res["total_restarts"]

    return SolveResult(
        algo="HC",
        init_state=res["initial_state"],
        final_state=res["final_state"],
        final_value=res["final_value"],
        value_history=clean(res["value_history"]),
        iterations=res["iterations"],
        duration=res["duration"],
        extra=extra,
    )