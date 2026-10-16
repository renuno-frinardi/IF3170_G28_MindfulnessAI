"""Kode untuk algoritma Steepest Ascent Hill-Climbing"""

import random
import time
from ...models.state import State
from ...utils.neighbor import random_neighbor

# Fungsi utama hill-climbing steepest ascent
def steepest_ascent_hill_climbing(initial_state: State, num_candidates: int = 50, seed=None) -> dict:
    rng = random.Random(seed)
    current = initial_state
    current.evaluate()

    value_history = [current.value]
    iterations = 0

    start = time.perf_counter()

    # Loop utama untuk iterasi steepest ascent
    while True:
        best = None
        best_value = current.value

        # Eksplorasi random neighbor sebanyak n dan mencari yang terbaik
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
        iterations += 1
        value_history.append(current.value)

    duration = time.perf_counter() - start

    # Mengembalikan format dictionary yang berisi data per state
    return {
        "initial_state": initial_state,
        "final_state": current,
        "final_value": current.value,
        "value_history": value_history,
        "iterations": iterations,
        "duration": duration,
    }
