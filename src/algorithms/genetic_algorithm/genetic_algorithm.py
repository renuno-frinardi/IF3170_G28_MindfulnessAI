# Import
import random
from time import perf_counter
from src.models.state import State
from src.utils.state_utils import copy_state
from .helper_ga import (
    fitness_function,
    selection,
    crossover,
    mutation,
    objective_statistics,
    init_population,
)

# Main
def genetic_algorithm(packages, truck, pilihan, n, seed=None) -> dict[str, object]:
    rng = random.Random(seed)
    results = []

    if pilihan == "jumlah_populasi":
        jumlah_populasi = n
        if jumlah_populasi <= 0:
            raise ValueError("Jumlah populasi harus lebih besar dari nol")

        population = init_population(jumlah_populasi, packages, truck, rng=rng)

        for _ in range(3):
            iteration = rng.randint(1, 100)
            for _ in range(3):
                results.append(run_genetic_algorithm(population, iteration, rng=rng))
    else:
        iteration = n
        if iteration < 0:
            raise ValueError("Banyak iterasi tidak boleh negatif")

        for _ in range(3):
            jumlah_populasi = rng.randint(1, 100)
            population = init_population(jumlah_populasi, packages, truck, rng=rng)
            for _ in range(3):
                results.append(run_genetic_algorithm(population, iteration, rng=rng))

    return {
        "pilihan": pilihan,
        "nilai_kontrol": n,
        "results": results,
    }

# Helper: Process of one (1) genetic algorithm
def run_genetic_algorithm(population: list[State], iterations: int, rng=random) -> dict[str, object]:

    # 1. Menghitung wkatu mulai, ukuran populasi, dan skor fitness awal
    start = perf_counter()
    population_size = len(population)
    fitness_scores = [fitness_function(state) for state in population]

    # 2. Menentukan state awal dan sate terbaik beserta valuenya
    initial_best = population[0]
    initial_best_value = initial_best.objective_value()
    for state in population:
        value = state.objective_value()
        if value > initial_best_value:
            initial_best = state
            initial_best_value = value
    initial_state = copy_state(initial_best)
    best_state = copy_state(initial_best)
    best_objective = best_state.objective_value()

    # 3. Menyimpan nilai maksimum dan rata-rata value dari populasi awal
    maxobjective, avgobjective = objective_statistics(population)
    maxhistory = [maxobjective]
    avghistory = [avgobjective]

    for _ in range(iterations):
        # I. Selection
        parents = selection(population, fitness_scores, rng=rng)
        new_population = []

        # II. Crossover
        for index in range(0, population_size - 1, 2):
            child1, child2 = crossover(
                parents[index],
                parents[index + 1],
                rng=rng,
            )
            new_population.extend((child1, child2))

        if population_size % 2 == 1:
            new_population.append(copy_state(parents[-1]))

        # III. Mutation
        new_population = [mutation(individual, rng=rng) for individual in new_population]

        # Menghitung skor fitness dari populasi baru
        new_population_fitness = [fitness_function(state) for state in new_population]

        # Elitism (menyimpan state terbaik dari populasi sebelumnya)
        worst_index = 0
        worst_value = new_population_fitness[0]
        for index in range(population_size):
            if new_population_fitness[index] < worst_value:
                worst_index = index
                worst_value = new_population_fitness[index]
        best_fitness = fitness_function(best_state)
        if best_fitness > new_population_fitness[worst_index]:
            new_population[worst_index] = copy_state(best_state)
            new_population_fitness[worst_index] = best_fitness

        # Hasil Akhir Proses Iterasi
        population = new_population
        fitness_scores = new_population_fitness

        # [Informasi Statistik]
        generation_best = population[0]
        generation_best_objective = generation_best.objective_value()
        for state in population:
            value = state.objective_value()
            if value > generation_best_objective:
                generation_best = state
                generation_best_objective = value
                
        if generation_best_objective > best_objective:
            best_state = copy_state(generation_best)
            best_objective = generation_best_objective

        maxobjective, avgobjective = objective_statistics(population)
        maxhistory.append(maxobjective)
        avghistory.append(avgobjective)

    # Hasil Akhir
    best_state.evaluate()
    duration = perf_counter() - start

    return {
        "initial_state": initial_state,
        "final_state": best_state,
        "final_objective": best_objective,
        "objective_history": {
            "iteration": list(range(iterations + 1)),
            "maximum": maxhistory,
            "average": avghistory,
        },
        "population_size": population_size,
        "iterations": iterations,
        "duration_seconds": duration,
    }

