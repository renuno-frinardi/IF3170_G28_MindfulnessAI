import math
import time
from ...utils.neighbor import random_neighbor

# menurunkan temperatur seiring waktu
def schedule(t, t_start, alpha):
    return t_start * (alpha ** (t - 1))

# alpha digunakan untuk memperkecil temperatur
def simulated_annealing(init, rng, t_start=100.0, alpha=0.95, t_min=1e-2, max_iter=500) -> dict:
    init.evaluate()
    curr = init
    best = init
    history, probs = [], []
    stuck = 0
    start = time.time()

    for t in range(1, max_iter + 1):
        temp = schedule(t, t_start, alpha)
        if temp < t_min:
            break

        neighbor = random_neighbor(curr, rng)
        p = 0.0
        moved = False
        if neighbor is not None:
            neighbor.evaluate()
            if not math.isinf(neighbor.value):
                delta = neighbor.value - curr.value
                if delta > 0:
                    p = 1.0
                    curr = neighbor
                    moved = True
                else:
                    p = math.exp(delta / temp) # p = exp(delta/T)

                    # kalau random < p, pindah ke neighbor
                    if rng.random() < p:
                        curr = neighbor
                        moved = True

                if curr.value > best.value:
                    best = curr

        if not moved: # kalau curr tidak pindah, stuck bertambah 1
            stuck += 1

        history.append(curr.value)
        probs.append(p)

    return {
        "initial": init,
        "final": best,
        "history": history,
        "probs": probs,
        "stuck": stuck,
        "duration": time.time() - start,
    }