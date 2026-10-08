import random
from .state_utils import candidate, copy_state, try_place

# tukar 2 paket
def swap(state, rng):
    n = len(state.packages)
    inside = [i for i, p in enumerate(state.packages) if p.is_inside]
    if n < 2 or not inside:
        return None
    
    a = rng.choice(inside)
    b = rng.choice([i for i in range(n) if i != a])

    new = copy_state(state)
    pa, pb = new.packages[a], new.packages[b]
    pos_a = (pa.x, pa.y) if pa.is_inside else None
    pos_b = (pb.x, pb.y) if pb.is_inside else None
    pa.remove()
    pb.remove()

    if pos_a is not None and not try_place(new, pb, *pos_a):
        return None
    
    if pos_b is not None and not try_place(new, pa, *pos_b):
        return None
    
    return new

# pindah 1 paket ke kandidat dengan z terendah
def move(state, rng):
    new = copy_state(state)
    pkg = rng.choice(new.packages)
    if pkg.is_inside:
        pkg.remove()
        return new
    
    old = (pkg.x, pkg.y, pkg.z) if pkg.is_inside else None
    pkg.remove()
    xs, ys = candidate(new, pkg)
    if not (xs and ys):
        return None
    
    if not try_place(new, pkg, rng.choice(xs), rng.choice(ys)):
        return None
    
    if old is not None and (pkg.x, pkg.y, pkg.z) == old:
        return None
    
    return new

# rotasi 90 derajat terhadap suatu sumbu
def rotate(state, rng):
    new = copy_state(state)
    pkg = rng.choice(new.packages)
    orientation = rng.choice(["x", "y", "z"])
    if orientation == "x":
        pkg.orientation = pkg.orientation.rotate_x()
    elif orientation == "y":
        pkg.orientation = pkg.orientation.rotate_y()
    else:
        pkg.orientation = pkg.orientation.rotate_z()

    if pkg.is_inside:
        x, y = pkg.x, pkg.y
        pkg.remove()
        if not try_place(new, pkg, x, y):
            return None
        
    return new

# random move untuk mendapatkan neighbor state
def random_neighbor(state, rng=None, tries=10):
    if rng is None:
        rng = random.Random()
    choices = ["move", "rotate"]
    if len(state.packages) >= 2:
        choices.append("swap")

    for _ in range(tries):
        moves = rng.choice(choices)
        if moves == "swap":
            new = swap(state, rng)
        elif moves == "move":
            new = move(state, rng)
        else:
            new = rotate(state, rng)
        if new is not None:
            return new
    
    return None