## Import
import random
from bisect import bisect_right
from copy import deepcopy
from math import isfinite

from src.models.state import State
from src.utils.neighbor import random_neighbor
from src.utils.state_utils import copy_state, random_initial_state


## STATIC VARIABLE
MUTATION_RATE = 0.05
MAX_MUTATION_ATTEMPTS = 10


## Prerequisite
# A. Fitness Function and Selection
def calculate_penalty(self: State) -> float:
    # [!] PR - Tentuin Penaltynya
    return 0

def fitness_function(self: State) -> float:
    value = float(sum(p.value for p in self.packages if p.is_inside))
    penalty = calculate_penalty(self)
    return value - penalty

def selection(population: list[State]) -> list[State]:
    # Wheel Random
    n = len(population)
    if n == 0:
        return []

    fitness_scores = [fitness_function(individual) for individual in population]
    if not all(isfinite(score) for score in fitness_scores):
        raise ValueError("Fitness must contain only finite numbers")

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
        population[bisect_right(cumulative_probabilities, random.random())]
        for _ in range(n)
    ]
    return parents

# B. Initialize Population
def init_population(n, packages, truck):
    population = []
    for i in range(n):
        population.append(random_initial_state(packages, truck))
    return population

# C. Crossover
def crossover(parent1: State, parent2: State) -> tuple[State,State]:
    point = random.randint(1,len(parent1.packages)-1)

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

    return child1,child2

# D. Mutation
def mutation(state: State, rng=random) -> State:
    if not state.packages or rng.random() >= MUTATION_RATE:
        return state

    for _ in range(MAX_MUTATION_ATTEMPTS):
        mutated = random_neighbor(state, rng=rng, tries=1)
        if mutated is not None and isfinite(mutated.evaluate()):
            return mutated

    return state

    

## Proses 
def genetic_algorithm(packages, truck, pilihan, n) -> State:
    
    
    if (pilihan == "jumlah_populasi"):
        jumlah_populasi = n

        # List of State
        population = init_population(jumlah_populasi, packages, truck)

        # Algoritma Utama - Genetic Algorithm
        for i in range (3):
            iteration = random.randint(1,100)

            new_population = deepcopy(population)
            for j in range (iteration):
                # 1. Selection 
                parents = selection(new_population)
                
                # 2. Crossover (one point crossover)
                for i in range(0, len(parents)-2, 2):
                    # [!] Belum handle odd
                    parent1 = parents[i]
                    parent2 = parents[i+1]

                    child1,child2 = crossover(parent1,parent2)
                    parents[i] = child1
                    parents[i+1] = child2

                # 3. Mutation 
                for index, individual in enumerate(parents):
                    parents[index] = mutation(individual)

                # 4. Hasil Akhir
                new_population = parents
    else:
        iteration = n
        for i in range (3):
            jumlah_populasi = random.randint(1,100)
            population = init_population(jumlah_populasi, packages, truck)

            new_population = deepcopy(population)
            for j in range (iteration):
                # 1. Selection 
                parents = selection(new_population)
                
                # 2. Crossover (one point crossover)
                for i in range(0, len(parents)-2, 2):
                    # [!] Belum handle odd
                    parent1 = parents[i]
                    parent2 = parents[i+1]

                    child1,child2 = crossover(parent1,parent2)
                    parents[i] = child1
                    parents[i+1] = child2

                # 3. Mutation 
                for index, individual in enumerate(parents):
                    parents[index] = mutation(individual)

                # 4. Hasil Akhir
                    new_population = parents


    return 0
