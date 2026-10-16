## Import
import random
from bisect import bisect_right
from copy import deepcopy
from math import isfinite
from time import perf_counter

from src.models.state import State
from src.utils.neighbor import random_neighbor
from src.utils.state_utils import copy_state, random_initial_state
from src.utils.validator import violations


## STATIC VARIABLE
MUTATION_RATE = 0.05
MAX_MUTATION_ATTEMPTS = 10


## Prerequisite
# A. Fitness Function and Selection
def calculate_penalty(state: State) -> float:
    violation_count = len(violations(state))
    if violation_count == 0:
        return 0.0

    maximum_objective = sum(max(0, package.value) for package in state.packages)
    return float((maximum_objective + 1) * violation_count)

def fitness_function(state: State) -> float:
    return state.objective_value() - calculate_penalty(state)

def selection(population: list[State], fitness_scores: list[float] | None = None, rng=random) -> list[State]:
    # Wheel Random
    n = len(population)
    if n == 0:
        return []

    if fitness_scores is None:
        fitness_scores = [fitness_function(individual) for individual in population]
    elif len(fitness_scores) != n:
        raise ValueError("Population dan Fitness Scores harus mempunyai panjang yang sama")

    if not all(isfinite(score) for score in fitness_scores):
        raise ValueError("Fitness Scores harus finite")

    # Roulette-wheel weights cannot be negative
    minimum_fitness = min(fitness_scores)
    if minimum_fitness < 0:
        weights = [score - minimum_fitness for score in fitness_scores]
    else:
        weights = fitness_scores

    total = sum(weights)
    if total == 0:
        probabilities = [1.0 / n] * n
    else:
        probabilities = [weight / total for weight in weights]

    # Convert [p1, p2, ...] into wheel boundaries [p1, p1+p2, ...].
    cumulative_probabilities = []
    cumulative = 0.0
    for probability in probabilities:
        cumulative += probability
        cumulative_probabilities.append(cumulative)

    # Avoid a floating-point gap at the end of the wheel.
    cumulative_probabilities[-1] = 1.0

    # bisect_right finds the wheel interval in O(log n) per draw.
    parents = [
        population[bisect_right(cumulative_probabilities, rng.random())]
        for _ in range(n)
    ]
    return parents

# B. Initialize Population
def init_population(n, packages, truck, rng=random):
    return [
        random_initial_state(packages, truck, seed=rng.randrange(2**63))
        for _ in range(n)
    ]

# C. Crossover
def crossover(parent1: State, parent2: State, rng=random) -> tuple[State, State]:
    parent1_ids = [package.id for package in parent1.packages]
    parent2_ids = [package.id for package in parent2.packages]
    if parent1_ids != parent2_ids:
        raise ValueError("Parents harus mempunyai urutan paket yang sama")

    if len(parent1.packages) < 2:
        return copy_state(parent1), copy_state(parent2)

    point = rng.randint(1, len(parent1.packages) - 1)

    child1 = State(
        packages=(
            deepcopy(parent1.packages[:point]) + deepcopy(parent2.packages[point:])
        ),
        truck=deepcopy(parent1.truck)
    )

    child2 = State(
        packages=(
            deepcopy(parent2.packages[:point]) + deepcopy(parent1.packages[point:])
        ),
        truck=deepcopy(parent2.truck)
    )

    if not isfinite(child1.evaluate()):
        child1 = copy_state(parent1)
    if not isfinite(child2.evaluate()):
        child2 = copy_state(parent2)

    return child1, child2

# D. Mutation
def mutation(state: State, rng=random) -> State:
    if not state.packages or rng.random() >= MUTATION_RATE:
        return state

    for _ in range(MAX_MUTATION_ATTEMPTS):
        mutated = random_neighbor(state, rng=rng, tries=1)
        if mutated is not None and isfinite(mutated.evaluate()):
            return mutated

    return state


def objective_statistics(population: list[State]) -> tuple[float, float]:
    objectives = [state.objective_value() for state in population]
    return max(objectives), sum(objectives) / len(objectives)


def run_genetic_algorithm(population: list[State], iterations: int, rng=random) -> dict[str, object]:

    # 1. Menghitung wkatu mulai, ukuran populasi, dan skor fitness awal
    started_at = perf_counter()
    population_size = len(population)
    fitness_scores = [fitness_function(state) for state in population]

    # 2. Menentukan state awal dan sate terbaik beserta valuenya
    initial_best = max(population, key=lambda state: state.objective_value())
    initial_state = copy_state(initial_best)
    best_state = copy_state(initial_best)
    best_objective = best_state.objective_value()

    # 3. Menyimpan nilai maksimum dan rata-rata value dari populasi awal
    maximum_objective, average_objective = objective_statistics(population)
    maximum_history = [maximum_objective]
    average_history = [average_objective]

    for _ in range(iterations):
        parents = selection(population, fitness_scores, rng=rng)
        new_population = []

        for index in range(0, population_size - 1, 2):
            child1, child2 = crossover(
                parents[index],
                parents[index + 1],
                rng=rng,
            )
            new_population.extend((child1, child2))

        if population_size % 2 == 1:
            new_population.append(copy_state(parents[-1]))

        new_population = [mutation(individual, rng=rng) for individual in new_population]
        new_population_fitness = [fitness_function(state) for state in new_population]

        # Elitism
        worst_index = min(range(population_size), key=new_population_fitness.__getitem__)
        best_fitness = fitness_function(best_state)
        if best_fitness > new_population_fitness[worst_index]:
            new_population[worst_index] = copy_state(best_state)
            new_population_fitness[worst_index] = best_fitness

        # Hasil Akhir Proses Iterasi
        population = new_population
        fitness_scores = new_population_fitness

        # [Informasi Statistik]
        generation_best = max(population, key=lambda state: state.objective_value())
        generation_best_objective = generation_best.objective_value()
        if generation_best_objective > best_objective:
            best_state = copy_state(generation_best)
            best_objective = generation_best_objective

        maximum_objective, average_objective = objective_statistics(population)
        maximum_history.append(maximum_objective)
        average_history.append(average_objective)

    # Hasil Akhir
    best_state.evaluate()
    duration_seconds = perf_counter() - started_at

    return {
        "initial_state": initial_state,
        "final_state": best_state,
        "final_objective": best_objective,
        "objective_history": {
            "iteration": list(range(iterations + 1)),
            "maximum": maximum_history,
            "average": average_history,
        },
        "population_size": population_size,
        "iterations": iterations,
        "duration_seconds": duration_seconds,
    }


## Proses
def genetic_algorithm(packages, truck, pilihan, n) -> dict[str, object]:
    results = []

    if pilihan == "jumlah_populasi":
        jumlah_populasi = n
        if jumlah_populasi <= 0:
            raise ValueError("Jumlah populasi harus lebih besar dari nol")

        population = init_population(jumlah_populasi, packages, truck)

        for _ in range(3):
            iteration = random.randint(1, 100)
            results.append(run_genetic_algorithm(population, iteration))
    else:
        iteration = n
        if iteration < 0:
            raise ValueError("Banyak iterasi tidak boleh negatif")

        for _ in range(3):
            jumlah_populasi = random.randint(1, 100)
            population = init_population(jumlah_populasi, packages, truck)
            results.append(run_genetic_algorithm(population, iteration))

    return {
        "pilihan": pilihan,
        "nilai_kontrol": n,
        "results": results,
    }
