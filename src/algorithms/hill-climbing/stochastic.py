"""Kode untuk algoritma Stochastic Hill-Climbing"""

# Import library
import random
import time
from ...models.state import State
from ...utils.neighbor import random_neighbor

# Fungsi utama untuk menjalankan algoritma stochastic HC
def stochastic_hill_climbing(initial_state: State, nmax: int = 1000, seed=None) -> dict:
    rng = random.Random(seed)
    current = initial_state
    current.evaluate()

    value_history = [current.value]

    start = time.perf_counter()

    # Iterasi stochastic HC sebanyak n kali
    for _ in range(nmax):
        cand = random_neighbor(current, rng)
        if cand is None:
            value_history.append(current.value)
            continue
        cand.evaluate()
        if cand.value > current.value:
            current = cand
        value_history.append(current.value)

    duration = time.perf_counter() - start

    # Mengembalikan format dictionary yang berisi data per state
    return {
        "initial_state": initial_state,
        "final_state": current,
        "final_value": current.value,
        "value_history": value_history,
        "iterations": nmax,
        "duration": duration,
    }
