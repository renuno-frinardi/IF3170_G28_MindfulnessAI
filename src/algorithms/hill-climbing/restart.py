"""Kode untuk algoritma random restart Hill-Climbing"""

# Import library
import random
import time
from ...models.state import State
from ...models.truck import Truck
from ...utils.neighbor import random_neighbor
from ...utils.state_utils import random_initial_state

# Fungsi untuk satu run steepest ascent
def steepest_ascent(current: State, rng: random.Random, num_candidates: int):
    current.evaluate()
    history = [current.value]
    iters = 0
    while True:
        best = None
        best_value = current.value
        for _ in range(num_candidates):
            cand = random_neighbor(current, rng)
            if cand is None:
                continue
            cand.evaluate()
            if cand.value > best_value:
                best = cand
                best_value = cand.value
        if best is None or best_value <= current.value:
            break
        current = best
        iters += 1
        history.append(current.value)
    return current, iters, history

# Fungsi utama untuk algirtma random restart
def random_restart_hill_climbing(packages, truck: Truck, max_restart: int = 10, num_candidates: int = 50, seed=None) -> dict:
    rng = random.Random(seed)
    start = time.perf_counter()

    best_overall = None
    first_state = None
    iterations_per_restart = []
    all_histories = []
    best_history = []
    total_iters = 0

    # Outer loop sebagai maksimum random restart
    for _ in range(max_restart):
        restart_seed = rng.randint(0, 2**31 - 1)
        init = random_initial_state(packages, truck, seed=restart_seed)
        if first_state is None:
            first_state = init

        # Memanggil inner loop untuk iterasi
        final, iters, history = steepest_ascent(init, rng, num_candidates)

        iterations_per_restart.append(iters)
        all_histories.append(history)
        total_iters += iters

        if best_overall is None or final.value > best_overall.value:
            best_overall = final
        best_history.append(best_overall.value)

    duration = time.perf_counter() - start

    # Mengembalikan format dictionary yang berisi data per state
    return {
        "initial_state": first_state,
        "final_state": best_overall,
        "final_value": best_overall.value if best_overall is not None else float("-inf"),
        "value_history": best_history,
        "all_histories": all_histories,
        "iterations": total_iters,
        "iterations_per_restart": iterations_per_restart,
        "total_restarts": max_restart,
        "duration": duration,
    }
