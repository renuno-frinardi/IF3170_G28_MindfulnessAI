import random
from ..models.package import Package
from ..models.state import State
from ..models.truck import Truck
from ..types.dimension import Dimension
from ..types.orientation import Orientation
from ..utils.validator import is_feasible

# 6 kemungkinan orientasi paket
ORIENTATIONS = [
    ("w", "l", "h"), ("w", "h", "l"), ("l", "w", "h"),
    ("l", "h", "w"), ("h", "w", "l"), ("h", "l", "w"),
]

# orientasi random
def random_orientation(rng) -> Orientation:
    w, l, h = rng.choice(ORIENTATIONS)
    return Orientation((w, l, h))

# kandidat dengan posisi paket yang muat dalam truk
def candidate(state, p) -> tuple[list[int], list[int]]:
    dim_w, dim_l, _ = p.dimension.get_dimensions(p.orientation.orientation)
    xs, ys = {0}, {0}
    for q in state.packages:
        if not q.is_inside or q.id == p.id:
            continue

        pos = q.get_position()
        if pos is None:
            continue

        x0, y0, _, x1, y1, _ = pos
        xs.update((x0, x1, x1 - dim_w))
        ys.update((y0, y1, y1 - dim_l))

    t = state.truck.dimension
    xs = sorted(x for x in xs if 0 <= x and x + dim_w <= t.w)
    ys = sorted(y for y in ys if 0 <= y and y + dim_l <= t.l)
    return xs, ys

# z terendah di (x, y)
def low_z(state, p, x, y) -> int:
    dim_w, dim_l, _ = p.dimension.get_dimensions(p.orientation.orientation)
    z = 0 
    for q in state.packages:
        if not q.is_inside or q.id == p.id:
            continue

        pos = q.get_position()
        if pos is None:
            continue

        x0, y0, _, x1, y1, z1 = pos
        if max(x0, x) < min(x1, x + dim_w) and max(y0, y) < min(y1, y + dim_l):
            z = max(z, z1)
            
    return z

# taruh p di (x, y) dengan z terendah yang mungkin, false jika keluar truk
def try_place(state, p, x, y) -> bool:
    z = low_z(state, p, x, y)
    p.place(x, y, z)
    if not state.truck.is_in_truck(p):
        p.remove()
        return False
    return True

# copy state agar tidak merusak state awal
def copy_state(state) -> State:
    new_packages = []
    for p in state.packages:
        q = Package(
            id=p.id,
            dimension=Dimension(p.dimension.w, p.dimension.l, p.dimension.h),
            orientation=Orientation(p.orientation.orientation),
            value=p.value,
            weight=p.weight,
            is_fragile=p.is_fragile,
            eta=p.eta,
        )
        if p.is_inside:
            q.place(p.x, p.y, p.z)
        new_packages.append(q)

    new_truck = Truck(dimension=Dimension(
        state.truck.dimension.w, 
        state.truck.dimension.l, 
        state.truck.dimension.h,
    ), max_capacity=state.truck.max_capacity)

    return State(new_packages, new_truck, state.value)

# random state awal
def random_initial_state(package, truck, seed=None, tries=10) -> State:
    rng = random.Random(seed)
    new_truck = Truck(dimension=Dimension(
        truck.dimension.w,
        truck.dimension.l,
        truck.dimension.h,
    ), max_capacity=truck.max_capacity)

    new_packages = []
    for p in package:
        q = Package(
            id=p.id,
            dimension=Dimension(p.dimension.w, p.dimension.l, p.dimension.h),
            orientation=random_orientation(rng),
            value=p.value,
            weight=p.weight,
            is_fragile=p.is_fragile,
            eta=p.eta,
        )
        new_packages.append(q)

    state = State(new_packages, new_truck)

    order = list(range(len(new_packages)))
    rng.shuffle(order)

    for idx in order:
        q = new_packages[idx]
        for _ in range(tries):
            q.orientation = random_orientation(rng)
            dim_w, dim_l, dim_h = q.dimension.get_dimensions(q.orientation.orientation)
            
            # skip jika paket tidak muat dalam truk
            if (dim_w > new_truck.dimension.w or dim_l > new_truck.dimension.l or dim_h > new_truck.dimension.h):
                continue

            # pasti tidak melayang
            x = rng.randint(0, new_truck.dimension.w - dim_w)
            y = rng.randint(0, new_truck.dimension.l - dim_l)
            z = 0

            q.place(x, y, z)
            if is_feasible(state):
                break
            q.remove()

    state.evaluate()
    return state