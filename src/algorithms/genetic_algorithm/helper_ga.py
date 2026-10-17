## Import
import random
from bisect import bisect_right
from copy import deepcopy
from math import isfinite

from src.models.state import State
from src.utils.validator import violations
from src.utils.neighbor import random_neighbor
from src.utils.state_utils import copy_state, random_initial_state

## STATIC VARIABLE
MUTATION_RATE = 0.05
MAX_MUTATION_ATTEMPTS = 10


## Helper Functions
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
    # 1. Check population size and it's fitness scores
    n = len(population)
    if n == 0:
        return []

    if fitness_scores is None:
        fitness_scores = [fitness_function(individual) for individual in population]
    elif len(fitness_scores) != n:
        raise ValueError("Population dan Fitness Scores harus mempunyai panjang yang sama")

    if not all(isfinite(score) for score in fitness_scores):
        raise ValueError("Fitness Scores harus finite")

    # 2. Calculate probabilities for selection (using roulette wheel selection)
    minimum_fitness = min(fitness_scores)
    if minimum_fitness < 0:
        minimum_fitness -= 1 # Memastikan tidak ada yang punya weight 0
        weights = [score - minimum_fitness for score in fitness_scores]
    else:
        weights = fitness_scores

    total = sum(weights)
    if total == 0:
        probabilities = [1.0 / n] * n
    else:
        probabilities = [weight / total for weight in weights]

    # 3. Preparation and Selection Process
    # Convert [p1, p2, ...] into wheel boundaries [p1, p1+p2, ...].
    cumulative_probabilities = []
    cumulative = 0.0
    for probability in probabilities:
        cumulative += probability
        cumulative_probabilities.append(cumulative)

    # Avoid a floating-point gap at the end of the wheel.
    cumulative_probabilities[-1] = 1.0

    # Binary Search algorithm (bisec_right) to find the index of the selected parent based on random number
    parents = [ population[bisect_right(cumulative_probabilities, rng.random())] for _ in range(n) ]
    return parents

# B. Initialize Population
def init_population(n, packages, truck, rng=random):
    return [random_initial_state(packages, truck, seed=rng.randrange(2**63)) for _ in range(n)]

# C. Crossover
def crossover(parent1: State, parent2: State, rng=random) -> tuple[State, State]:
    # 1. Move parent into variable inside function
    parent1_ids = [package.id for package in parent1.packages]
    parent2_ids = [package.id for package in parent2.packages]
    if parent1_ids != parent2_ids:
        raise ValueError("Parents harus mempunyai urutan paket yang sama")

    if len(parent1.packages) < 2:
        return copy_state(parent1), copy_state(parent2)

    # 2. Choosing crossover point
    point = rng.randint(1, len(parent1.packages) - 1)

    # 3. Crossover process (main)
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

    # 4. Validation and Return
    if not isfinite(child1.evaluate()):
        child1 = copy_state(parent1)
    if not isfinite(child2.evaluate()):
        child2 = copy_state(parent2)

    return child1, child2

# D. Mutation
def mutation(state: State, rng=random) -> State:
    # 1. Check probability 
    if not state.packages or rng.random() >= MUTATION_RATE:
        return state

    # 2. Mutation process with maximum tries is MAX_MUTATION_ATTEMPTS
    for _ in range(MAX_MUTATION_ATTEMPTS):
        mutated = random_neighbor(state, rng=rng, tries=1)
        if mutated is not None and isfinite(mutated.evaluate()):
            return mutated

    return state

# E. Statistic Helper (for the required data in result's report)
def objective_statistics(population: list[State]) -> tuple[float, float]:
    objectives = [state.objective_value() for state in population]
    return max(objectives), sum(objectives) / len(objectives)