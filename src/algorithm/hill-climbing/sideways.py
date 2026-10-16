"""Kode untuk algoritma Hill-Climbing dengan sideways move"""

# Import library
import random
import time
from ...models.state import State
from ...utils.neighbor import random_neighbor

# Fungsi utama untuk run sideways move HC
def sideways_move_hill_climbing(initial_state: State, num_candidates: int = 50, max_sideways: int = 100, seed=None) -> dict:
    rng = random.Random(seed)
    current = initial_state
    current.evaluate()

    value_history = [current.value]
    iterations = 0
    sideways_moves = 0

    start = time.perf_counter()

    # Outer loop untuk iterasi algoritma
    while True:
        best = None
        best_value = current.value

        # Inner loop untuk mencari n neighbor dan memilih yang terbaik
        for _ in range(num_candidates):
            cand = random_neighbor(current, rng)
            if cand is None:
                continue
            cand.evaluate()
            if best is None or cand.value > best_value:
                best = cand
                best_value = cand.value

        if best is None or best_value < current.value:
            break

        # Iterasi terus menerus sampai mencapai batas max sideways
        if best_value == current.value:
            if sideways_moves >= max_sideways:
                break
            sideways_moves += 1
        else:
            sideways_moves = 0

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
        "sideways_moves": sideways_moves,
        "duration": duration,
    }
