import math
import random
from dataclasses import asdict, dataclass, field, replace
from .algorithms.genetic_algorithm.genetic_algorithm import genetic_algorithm
from .algorithms.hill_climbing.restart import random_restart_hill_climbing
from .algorithms.hill_climbing.sideways import sideways_move_hill_climbing
from .algorithms.hill_climbing.steepest_ascent import steepest_ascent_hill_climbing
from .algorithms.hill_climbing.stochastic import stochastic_hill_climbing
from .algorithms.simulated_annealing.simulated_annealing import simulated_annealing
from .models.package import Package
from .models.state import State
from .objective import DEFAULT_OBJECTIVE, validate_objective
from .parser.main import Problem
from .types.dimension import Dimension
from .types.orientation import Orientation
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
    init_states: list[State] = field(default_factory=list)
    final_states: list[State] = field(default_factory=list)

def clean(history) -> list[float | None]: # nilai -inf diubah jadi None
    return [None if (isinstance(v, float) and math.isinf(v) and v < 0) else v for v in history]

# Mengambil salinan paket yang masih di luar (not is_inside) untuk truk berikutnya
def unloaded_packages(state: State) -> list[Package]:
    return [
        Package(
            id=p.id,
            dimension=Dimension(p.dimension.w, p.dimension.l, p.dimension.h),
            orientation=Orientation(p.orientation.orientation),
            value=p.value,
            weight=p.weight,
            is_fragile=p.is_fragile,
            eta=p.eta,
        )
        for p in state.packages
        if not p.is_inside
    ]

# Fungsi untuk solve 1 truk (akan dipanggil di fungsi solve())
def solve_single_truck(algo: str, problem, seed: int | None, objective_mode: str) -> SolveResult:
    if algo == "SA":
        return solve_sa(problem, seed, objective_mode)
    if algo == "GA":
        return solve_ga(problem, seed, objective_mode)
    if algo == "HC":
        return solve_hc(problem, seed, objective_mode)
    raise ValueError(f"Algoritma tidak dikenal: '{algo}'")

# Fungsi untuk solve multi-truk (main function)
def solve(parsed: Problem, seed: int | None = None, objective_mode: str = DEFAULT_OBJECTIVE) -> SolveResult:
    objective_mode = validate_objective(objective_mode)
    trucks = list(getattr(parsed.problem, "trucks", None) or [parsed.problem.truck])

    remaining = list(parsed.problem.packages)
    truck_results: list[SolveResult] = []

    # Iterasi semua truk
    for idx, truck in enumerate(trucks):
        if not remaining:
            break
        truck_seed = None if seed is None else seed + idx * 1000
        sub_problem = replace(parsed.problem, truck=truck, packages=remaining)
        res = solve_single_truck(parsed.algo, sub_problem, truck_seed, objective_mode)
        truck_results.append(res)
        remaining = unloaded_packages(res.final_state)

    init_states = [r.init_state for r in truck_results]
    final_states = [r.final_state for r in truck_results]

    # Case: 1 truk saja dan langsung return
    if len(truck_results) == 1:
        res = truck_results[0]
        res.init_states = init_states
        res.final_states = final_states
        res.extra["trucks"] = trucks
        return res

    # Case: multi-truk dan gabungkan hasilnya
    first, last = truck_results[0], truck_results[-1]
    extra = dict(first.extra)
    extra["trucks"] = trucks
    extra["truck_histories"] = [r.value_history for r in truck_results]

    # Informasi Statistik (tambahan) untuk tiap algoritma
    if parsed.algo == "SA":
        extra["stuck"] = sum(r.extra["stuck"] for r in truck_results)
        extra["probs"] = [p for r in truck_results for p in r.extra["probs"]]
        extra["truck_init_values"] = [r.init_state.value for r in truck_results]
        extra["truck_probs"] = [r.extra["probs"] for r in truck_results]
        best_states = [r.extra["best_state"] for r in truck_results if r.extra.get("best_state") is not None]
        extra["best_states"] = best_states if len(best_states) == len(truck_results) else None
    elif parsed.algo == "HC":
        if "sideways_moves" in first.extra:
            extra["sideways_moves"] = sum(r.extra.get("sideways_moves", 0) for r in truck_results)
        if "all_histories" in first.extra:
            extra["all_histories"] = [h for r in truck_results for h in r.extra["all_histories"]]
            extra["iterations_per_restart"] = [it for r in truck_results for it in r.extra["iterations_per_restart"]]
            extra["total_restarts"] = sum(r.extra["total_restarts"] for r in truck_results)
    elif parsed.algo == "GA":
        combined_results = []
        for i in range(len(first.extra["results"])):
            r_inits = [tr.init_state for tr in truck_results[:-1]] + [last.extra["results"][i]["initial_state"]]
            r_finals = [tr.final_state for tr in truck_results[:-1]] + [last.extra["results"][i]["final_state"]]
            base_run = dict(last.extra["results"][i])
            base_run["initial_states"] = r_inits
            base_run["final_states"] = r_finals
            base_run["final_objective"] = sum(s.value for s in r_finals)
            base_run["duration_seconds"] = sum(tr.extra["results"][i]["duration_seconds"] for tr in truck_results)
            base_run["trucks"] = trucks
            combined_results.append(base_run)
        extra["results"] = combined_results

    # Return untuk multitruk
    return SolveResult(
        algo=parsed.algo,
        init_state=init_states[0],
        final_state=final_states[-1],
        final_value=sum(s.value for s in final_states),
        value_history=[v for r in truck_results for v in r.value_history],
        iterations=sum(r.iterations for r in truck_results),
        duration=sum(r.duration for r in truck_results),
        extra=extra,
        init_states=init_states,
        final_states=final_states,
    )

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